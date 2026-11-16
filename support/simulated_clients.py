"""Independent local LLM client simulation; never labelled official GigSim."""

import hashlib
import json
import os
import random
import time
import httpx
from core import db
from core.settings import ROOT, config
from core.security import mask


def preferences(job):
    rng = random.Random(int(hashlib.sha256(("client-v1:" + job["id"]).encode()).hexdigest()[:16], 16))
    skills = list(job.get("skills", []))
    must = sorted(rng.sample(skills, min(len(skills), rng.randint(1, 3)))) if skills else []
    low = float(job.get("budget_min") or 20)
    high = float(job.get("budget_max") or low)
    return {
        "must_have_skills": must,
        "hourly_ceiling": round(low + (high - low) * rng.uniform(0.35, 0.95), 2),
        "dislikes_generic_opening": rng.choice([True, False]),
        "priority": rng.choice(["validation plan", "relevant delivered work", "clear scope questions"]),
        "provenance": "Synthetic private client preferences; independently seeded, not gold labels",
    }


async def judge_proposal(job, text, amount, evidence, model=None):
    private = preferences(job)
    model = model or config()["models"]["profiles"]["open"]["critic"]
    prompt = (ROOT / "agent/prompts/simulated_client.v1.md").read_text()
    schema = {
        "type": "object",
        "properties": {
            "stage": {"type": "string", "enum": ["ignored", "replied", "interview", "hired"]},
            "reason": {"type": "string"},
            "message": {"type": "string"},
        },
        "required": ["stage", "reason", "message"],
        "additionalProperties": False,
    }
    payload = {
        "model": model,
        "stream": False,
        "messages": [
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": "<untrusted_experiment_data>"
                + json.dumps(
                    {
                        "job": {k: v for k, v in job.items() if k not in ("persona_hint", "gold")},
                        "proposal": text,
                        "hourly_amount": amount,
                        "source_evidence": evidence,
                        "private_preferences": private,
                    }
                )
                + "</untrusted_experiment_data>",
            },
        ],
        "format": schema,
        "options": {"temperature": 0, "seed": 4016, "num_ctx": 4096, "num_predict": 280},
        "keep_alive": "10m",
    }
    start = time.perf_counter()
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(os.getenv("OLLAMA_URL", "http://127.0.0.1:11434") + "/api/chat", json=payload)
        response.raise_for_status()
        raw = response.json()
    result = json.loads(raw["message"]["content"])
    if result.get("stage") not in ("ignored", "replied", "interview", "hired"):
        raise ValueError("Invalid client decision")
    if amount > private["hourly_ceiling"]:
        result.update(stage="ignored", reason="Deterministic private budget ceiling exceeded", message="")
    return dict(
        result,
        model=model,
        synthetic=True,
        simulator="GigBid independently authored LLM client v1",
        seconds=time.perf_counter() - start,
        prompt_tokens=raw.get("prompt_eval_count", 0),
        completion_tokens=raw.get("eval_count", 0),
        api_usd=0,
        private_preferences=private,
    )


async def process_pending(tenant):
    """Runs in the background worker; receipts stop duplicate outcome/message creation."""
    from rag.index.engine import load_corpus
    from rag.verify import CITATION

    tasks = db.scan(tenant, "simulated_client_task")
    for task in tasks:
        if task.get("status") in ("done", "failed") or task.get("next_retry", 0) > time.time():
            continue
        proposal = db.get(tenant, "proposal", task["proposal_id"])
        if not proposal:
            continue
        from mcp_servers.marketplace.adapters.local_sim import jobs, lock

        job = db.get(tenant, "job", proposal["job_id"]) or next(
            (j for j in jobs() if j["id"] == proposal["job_id"]), None
        )
        if not job:
            continue
        try:
            ids = set(CITATION.findall(proposal["text"]))
            corpus = load_corpus() + db.scan(tenant, "evidence")
            evidence = [e for e in corpus if e["id"] in ids]
            outcome = await judge_proposal(job, proposal["text"], proposal["amount"], evidence)
            with db.connection() as conn:
                lock(conn, tenant)
                current = db.get(tenant, "simulated_client_task", task["id"], conn)
                if current.get("status") == "done":
                    continue
                db.put(
                    tenant,
                    "simulated_client_outcome",
                    proposal["id"],
                    dict(outcome, id=proposal["id"], job_id=job["id"]),
                    conn,
                )
                if outcome["stage"] != "ignored" and outcome["message"].strip():
                    mid = "client-" + proposal["id"]
                    db.put(
                        tenant,
                        "message",
                        mid,
                        {
                            "id": mid,
                            "conversation_id": job["id"],
                            "sender": "client",
                            "text": outcome["message"],
                            "created": time.time(),
                            "synthetic": True,
                            "source": "independent_local_llm_client",
                        },
                        conn,
                    )
                current.update(status="done")
                db.put(tenant, "simulated_client_task", task["id"], current, conn)
            from agent.memory.promotion_rules import record_outcome

            record_outcome(
                tenant,
                job.get("industry", "general"),
                "won" if outcome["stage"] == "hired" else ("ignored" if outcome["stage"] == "ignored" else "replied"),
                proposal["id"],
            )
        except Exception as error:
            attempt = task.get("attempts", 0) + 1
            task.update(
                status="retry" if attempt < 3 else "failed",
                attempts=attempt,
                next_retry=time.time() + 60 * attempt,
                error=mask(str(error))[:500],
            )
            db.put(tenant, "simulated_client_task", task["id"], task)


async def process_all_pending():
    with db.connection() as conn:
        rows = db.execute(conn, "SELECT DISTINCT tenant FROM documents WHERE kind='simulated_client_task'").fetchall()
    for row in rows:
        await process_pending(row["tenant"])
