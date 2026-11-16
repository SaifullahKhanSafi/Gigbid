import json
import os
import time
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import StreamingResponse
from core import db
from core.settings import config
from core.security import digest
from apps.api.auth.users import current_user, register, login
from apps.api.schemas.models import (
    Credentials,
    Session,
    Profile,
    StartRun,
    StartConversation,
    RunRecord,
    RunList,
    JobList,
    Health,
)
from agent.handoffs import Approval
from apps.api.service import create_run
from apps.api.streaming import stream_run
from worker.runner import enqueue
from rag.retriever import reindex
from rag.index.engine import load_corpus

router = APIRouter(prefix="/api")


@router.post("/oauth/upwork/start")
async def oauth_start(request: Request, user: str = Depends(current_user)):
    from apps.api.auth.oauth import begin_upwork

    if not os.getenv("OAUTH_ENCRYPTION_KEY"):
        raise HTTPException(503, "Configure server token encryption first")
    base = os.getenv("PUBLIC_BASE_URL", str(request.base_url).rstrip("/"))
    return await begin_upwork(user, base)


@router.get("/oauth/upwork/status/{flow_id}")
def oauth_status(flow_id: str, user: str = Depends(current_user)):
    from apps.api.auth.oauth import flows

    flow = flows.get(flow_id)
    if not flow or flow["tenant"] != user:
        raise HTTPException(404, "OAuth flow not found")
    return {"status": flow["status"], "tools": flow.get("tools", [])}


@router.get("/oauth/upwork/callback/{flow_id}")
async def oauth_callback(flow_id: str, code: str = "", state: str | None = None, error: str | None = None):
    from apps.api.auth.oauth import flows
    from fastapi.responses import HTMLResponse

    flow = flows.get(flow_id)
    if not flow or flow["callback"].done():
        raise HTTPException(400, "Expired OAuth callback")
    if error or not code:
        raise HTTPException(400, "Authorization was not completed")
    # The SDK validates the state and PKCE verifier against its pending flow.
    flow["callback"].set_result((code, state))
    return HTMLResponse(
        "<!doctype html><title>GigBid connection</title><p>Authorization received. Return to GigBid to check the connection.</p>"
    )


@router.get("/health", response_model=Health)
async def health():
    available = "available"
    if os.getenv("GIGBID_MCP_TRANSPORT") == "http":
        import httpx

        try:
            async with httpx.AsyncClient(timeout=2) as client:
                r = await client.post(os.getenv("MARKETPLACE_MCP_URL", "http://localhost:8102/mcp"))
                if r.status_code not in (400, 401, 403, 405, 406):
                    available = "unavailable"
        except Exception:
            available = "unavailable"
    return Health(
        status="ok",
        marketplace=available,
        mode=config()["marketplace"]["mode"],
        model_mode=os.getenv("GIGBID_MODEL_MODE", "ollama"),
    )


def auth_rate(request):
    key = digest({"ip": request.client.host if request.client else "local", "window": int(time.time() // 60)})
    with db.connection() as c:
        from mcp_servers.marketplace.adapters.local_sim import lock

        lock(c, "auth-rate")
        row = db.get("authentication", "rate", key, c) or {"count": 0}
        if row["count"] >= 20:
            raise HTTPException(429, "Too many authentication attempts; retry in a minute")
        db.put("authentication", "rate", key, {"count": row["count"] + 1}, c)


@router.post("/auth/register", response_model=Session)
def signup(body: Credentials, request: Request):
    auth_rate(request)
    return register(body.email, body.password)


@router.post("/auth/login", response_model=Session)
def signin(body: Credentials, request: Request):
    auth_rate(request)
    return login(body.email, body.password)


@router.get("/profile", response_model=Profile)
def profile(user: str = Depends(current_user)):
    return db.get(user, "settings", "profile") or Profile().model_dump()


@router.put("/profile", response_model=Profile)
def save_profile(body: Profile, user: str = Depends(current_user)):
    return db.put(user, "settings", "profile", body.model_dump())


@router.get("/jobs", response_model=JobList)
async def jobs(user: str = Depends(current_user), q: str = ""):
    from mcp_servers.marketplace.adapters.local_sim import jobs as local_jobs

    preferences = db.get(user, "settings", "profile") or {}
    persona = preferences.get("persona", "ml")
    mode = config()["marketplace"]["mode"]
    if mode == "local_sim":
        records = local_jobs() + db.scan(user, "job")
    else:
        from agent.mcp_client import ToolGateway, MarketplaceUnavailable
        import uuid

        try:
            async with ToolGateway(user, uuid.uuid4().hex) as gateway:
                result = await gateway.call(
                    "scout", "search_jobs", query=q or preferences.get("saved_search", ""), limit=50
                )
            for job in result.get("jobs", []):
                job = dict(job, synthetic=mode == "gigsim")
                needed = {"id", "title", "description", "skills", "budget_min", "budget_max", "connects"}
                if needed - set(job):
                    raise ValueError("Marketplace job mapping is incomplete: " + ", ".join(sorted(needed - set(job))))
                db.put(user, "job", job["id"], job)
            records = db.scan(user, "job")
        except (MarketplaceUnavailable, ValueError, PermissionError) as error:
            raise HTTPException(503, str(error)[:300]) from error
    runs = {r.get("job_id"): r for r in reversed(db.scan(user, "run")) if r["kind"] == "bid"}
    items = []
    for job in records:
        if (
            persona != "own" and not preferences.get("agency_mode") and job.get("persona_hint", persona) != persona
        ) or q.lower() not in (job["title"] + " " + job["description"]).lower():
            continue
        item = {
            k: job[k]
            for k in ["id", "title", "description", "skills", "budget_min", "budget_max", "connects", "synthetic"]
        }
        item["run"] = runs.get(job["id"])
        items.append(item)
    items.sort(key=lambda x: (x["run"] or {}).get("state", {}).get("fit", {}).get("score", -1), reverse=True)
    return {"jobs": items}


@router.post("/runs", response_model=RunRecord)
async def start(body: StartRun, user: str = Depends(current_user)):
    from mcp_servers.marketplace.adapters.local_sim import jobs as local_jobs

    known = {j["id"] for j in local_jobs() + db.scan(user, "job")}
    if body.job_id not in known:
        raise HTTPException(404, "Job not found")
    return await create_run(user, job_id=body.job_id)


@router.post("/conversations", response_model=RunRecord)
async def conversation(body: StartConversation, user: str = Depends(current_user)):
    if not any(x["conversation_id"] == body.conversation_id for x in db.scan(user, "message")):
        raise HTTPException(404, "Conversation not found")
    return await create_run(user, conversation_id=body.conversation_id)


@router.get("/runs", response_model=RunList)
def runs(user: str = Depends(current_user)):
    return {"runs": db.scan(user, "run")}


@router.get("/runs/{run_id}", response_model=RunRecord)
def run(run_id: str, user: str = Depends(current_user)):
    record = db.get(user, "run", run_id)
    if not record:
        raise HTTPException(404, "Run not found")
    return record


@router.get("/runs/{run_id}/events")
async def events(run_id: str, request: Request, user: str = Depends(current_user)):
    run(run_id, user)
    return StreamingResponse(
        stream_run(user, run_id, request),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/runs/{run_id}/approval", response_model=RunRecord)
async def approval(run_id: str, body: Approval, user: str = Depends(current_user)):
    record = run(run_id, user)
    if record["status"] != "awaiting_approval":
        raise HTTPException(409, "Run is not waiting for approval")
    if body.action == "reject" and not body.reason.strip():
        raise HTTPException(422, "A rejection reason is required")
    record.update(pending_approval=body.model_dump(), status="queued", updated=time.time())
    db.put(user, "run", run_id, record)
    db.audit(
        user, run_id, {"action": "human_" + body.action, "reason": body.reason, "edit_hash": digest(body.text or "")}
    )
    await enqueue(user, run_id)
    return record


@router.post("/runs/{run_id}/retry", response_model=RunRecord)
async def retry(run_id: str, user: str = Depends(current_user)):
    record = run(run_id, user)
    if record["status"] not in ("queued_retry", "needs_attention"):
        raise HTTPException(409, "Run does not need a retry")
    record.update(status="queued")
    db.put(user, "run", run_id, record)
    await enqueue(user, run_id)
    return record


@router.get("/evidence")
def evidence(user: str = Depends(current_user)):
    persona = (db.get(user, "settings", "profile") or {}).get("persona", "ml")
    deleted = {x["id"] for x in db.scan(user, "deleted_evidence")}
    return {
        "items": [
            x for x in load_corpus() + db.scan(user, "evidence") if x["persona"] == persona and x["id"] not in deleted
        ]
    }


@router.delete("/evidence/{id}")
def remove_evidence(id: str, user: str = Depends(current_user)):
    if not any(x["id"] == id for x in evidence(user)["items"]):
        raise HTTPException(404, "Evidence not found")
    db.put(user, "deleted_evidence", id, {"id": id})
    db.delete(user, "evidence", id)
    reindex(user)
    return {"deleted": id}


@router.post("/portfolio/upload")
async def upload(
    file: UploadFile = File(...),
    kind: str = Form("case_study"),
    skills: str = Form(""),
    industry: str = Form("general"),
    outcome: str = Form(""),
    user: str = Depends(current_user),
):
    import tempfile
    from rag.ingest.loaders import load_document

    allowed = {".pdf", ".md", ".txt", ".py", ".js", ".ts", ".json", ".sql"}
    suffix = Path(file.filename or "").suffix.lower()
    if kind not in ("cv", "case_study", "readme", "code", "review", "proposal") or outcome not in (
        "",
        "won",
        "replied",
        "ignored",
    ):
        raise HTTPException(422, "Invalid evidence type or outcome")
    if suffix not in allowed:
        raise HTTPException(422, "Unsupported file type")
    data = await file.read(3_000_001)
    if len(data) > 3_000_000:
        raise HTTPException(413, "Maximum upload size is 3 MB")
    profile = db.get(user, "settings", "profile") or {"persona": "ml"}
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / ("upload" + suffix)
        path.write_bytes(data)
        try:
            item = load_document(
                path,
                {
                    "persona": profile["persona"],
                    "type": kind,
                    "project": "uploaded-" + digest(data.hex())[:10],
                    "skills": [s.strip() for s in skills.split(",") if s.strip()],
                    "date": time.strftime("%Y-%m-%d"),
                    "industry": industry,
                    "synthetic": False,
                    "provenance": "User-uploaded evidence; authenticity not independently verified",
                    "outcome": outcome or None,
                },
            )
        except Exception as e:
            raise HTTPException(422, str(e)[:200]) from e
    item["source"] = (file.filename or "upload").replace("\\", "/").split("/")[-1]
    db.put(user, "evidence", item["id"], item)
    reindex(user)
    return {"id": item["id"], "indexed": True}


@router.get("/messages")
def messages(user: str = Depends(current_user)):
    return {"messages": db.scan(user, "message")}


@router.get("/pipeline")
def pipeline(user: str = Depends(current_user)):
    proposals = db.scan(user, "proposal")
    replied = {m["conversation_id"] for m in db.scan(user, "message") if m.get("sender") == "client"}
    outcomes = {x["id"]: x for x in db.scan(user, "simulated_client_outcome")}
    visible = [
        dict(p, status="replied") if p.get("job_id") in replied and p["status"] == "submitted" else p for p in proposals
    ]
    for proposal in visible:
        outcome = outcomes.get(proposal["id"])
        if outcome and outcome["stage"] != "ignored":
            proposal["status"] = outcome["stage"]
    return {"proposals": visible, "runs": db.scan(user, "run")}


@router.get("/memory")
def memory(user: str = Depends(current_user)):
    return {"style": db.scan(user, "memory_style"), "outcome": db.scan(user, "memory_outcome")}


@router.get("/connections")
def connections(user: str = Depends(current_user)):
    from apps.api.auth.oauth_store import load_tokens

    return {
        "marketplace_mode": config()["marketplace"]["mode"],
        "upwork_authorization_stored": bool(load_tokens(user, "upwork")),
        "live_tools_verified": False,
    }


@router.delete("/memory/{kind}/{id}")
def delete_memory(kind: str, id: str, user: str = Depends(current_user)):
    if kind not in ("style", "outcome"):
        raise HTTPException(422, "Unknown memory type")
    db.delete(user, "memory_" + kind, id)
    return {"deleted": id}


@router.get("/analytics")
def analytics(user: str = Depends(current_user)):
    import numpy as np

    records = db.scan(user, "run")
    proposals = db.scan(user, "proposal")
    wallet = db.get(user, "wallet", "balance") or {"balance": 120, "spent": 0}
    times = [r["state"].get("execution_seconds", 0) for r in records if r["state"].get("execution_seconds")]
    outcomes = db.scan(user, "simulated_client_outcome")
    result = {
        "jobs_analyzed": sum(bool(r["state"].get("decision")) for r in records),
        "proposals_submitted": sum(p["status"] == "submitted" for p in proposals),
        "connects": wallet,
        "p95_seconds": float(np.percentile(times, 95)) if times else None,
        "api_usd": 0,
        "official_gigsim_reply_rate": None,
        "local_fixture_replies": len(
            [
                m
                for m in db.scan(user, "message")
                if m.get("sender") == "client" and m.get("source") != "independent_local_llm_client"
            ]
        ),
        "note": "Fixture replies test plumbing; separately labelled LLM-client outcomes use synthetic preferences. Official GigSim reply/hire rates are unavailable.",
    }
    result["independent_local_simulator"] = {
        "evaluated": len(outcomes),
        "reply_rate": sum(o["stage"] != "ignored" for o in outcomes) / len(outcomes) if outcomes else None,
        "hire_rate": sum(o["stage"] == "hired" for o in outcomes) / len(outcomes) if outcomes else None,
        "official_gigsim": False,
        "note": "Synthetic LLM-client outcomes; model judgments, not observed human behavior.",
    }
    return result


@router.get("/traces/{trace_id}")
def trace(trace_id: str, user: str = Depends(current_user)):
    with db.connection() as c:
        rows = db.execute(
            c, "SELECT body,created FROM audit WHERE tenant=? AND trace=? ORDER BY created", (user, trace_id)
        ).fetchall()
    return {"trace_id": trace_id, "events": [dict(json.loads(r["body"]), created=r["created"]) for r in rows]}
