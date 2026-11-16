import time
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send, interrupt
from agent.state import BidState
from agent.handoffs import ProposalDraft, Critique, Approval
from agent.nodes.logic import analyze, assess_risk, fit_report, decide, quote, compliance, extractive_draft
from agent.model import generate
from core.security import token
from core.settings import config
from rag.verify import verify


def build_bid_graph(gateway, checkpointer, profile):
    async def observed(name, state, fn):
        start = time.perf_counter()
        output = await fn()
        usage = output.pop("_usage", {})
        return dict(
            output,
            steps=1,
            tokens=usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0),
            events=[
                {"node": name, "seconds": time.perf_counter() - start, "usage": usage, "trace_id": state["trace_id"]}
            ],
        )

    async def scout(s):
        async def run():
            job = await gateway.call("scout", "get_job", job_id=s["job_id"])
            return {"job": job, "status": "analysing", "revision": 0}

        return await observed("scout", s, run)

    async def analyst(s):
        async def run():
            spec = analyze(s["job"])
            # Model extraction can add needs, but cannot silently change known budgets or requirements.
            result = await generate("analyst", {"job": s["job"], "known_skills": spec.skills}, s["trace_id"])
            needs = result["output"].get("hidden_needs", [])
            if isinstance(needs, list):
                spec.hidden_needs = [str(x)[:300] for x in needs[:4]]
            return {"spec": spec.model_dump(), "_usage": result}

        return await observed("analyst", s, run)

    async def risk(s):
        async def run():
            history = await gateway.call("risk", "get_client_history", client_id=s["job"]["client_id"])
            return {"risk": assess_risk(s["job"]["description"], history).model_dump()}

        return await observed("risk", s, run)

    async def fit(s):
        async def run():
            if profile.get("agency_mode"):
                result = await gateway.call(
                    "fit", "rank_team", requirement=s["job"]["description"], requirements=s["job"].get("skills", [])
                )
                return {"fit": result["fit"], "persona": result["selected_persona"]}
            evidence = await gateway.call(
                "fit",
                "search_evidence",
                requirement=s["job"]["description"],
                requirements=s["job"].get("skills", []),
                k=5,
            )
            return {"fit": fit_report(s["job"].get("skills", []), evidence["items"]).model_dump()}

        return await observed("fit", s, run)

    def decision(s):
        if (
            s.get("steps", 0) >= config()["budgets"]["max_graph_steps"]
            or s.get("tokens", 0) > config()["budgets"]["max_tokens_per_job"]
        ):
            return {
                "status": "needs_attention",
                "error": "Run budget exceeded",
                "decision": {"action": "skip", "reasons": ["Run budget exceeded"]},
            }
        d = decide(s["fit"], s["risk"], s["spec"]["budget_max"], profile.get("floor_rate", 20))
        return {"decision": d.model_dump(), "status": "skipped" if d.action == "skip" else "drafting"}

    async def pricing(s):
        async def run():
            balance = await gateway.call("pricing", "get_connects_balance")
            price = quote(s["job"], profile.get("floor_rate", 20), profile.get("market_median", 45))
            if balance["balance"] < price.connects:
                price.viable = False
            return {"price": price.model_dump(), "status": "drafting" if price.viable else "needs_attention"}

        return await observed("pricing", s, run)

    async def writer(s):
        async def run():
            result = await generate(
                "writer",
                {
                    "job": s["spec"],
                    "evidence": s["fit"]["evidence"],
                    "critique": s.get("critique"),
                    "style_memory": profile.get("style_memory", []),
                },
                s["trace_id"],
            )
            plan = result["output"].get("plan", "")
            if not isinstance(plan, str):
                plan = ""
            text = extractive_draft(s["job"], s["fit"]["evidence"], plan)
            answer = next(
                (f"{e['approved_claims'][0]} [{e['id']}]" for e in s["fit"]["evidence"] if e.get("approved_claims")),
                "Could you clarify the evidence you need for this question?",
            )
            answers = {q: answer for q in s["spec"].get("screening_questions", [])[:20]}
            revision = s.get("revision", 0) + (1 if s.get("draft") else 0)
            return {
                "draft": ProposalDraft(text=text, screening_answers=answers, version=revision + 1).model_dump(),
                "revision": revision,
                "_usage": result,
            }

        return await observed("writer", s, run)

    def verifier(s):
        verified = verify(s["draft"]["text"], s["fit"]["evidence"], s["draft"]["version"])
        verified.screening_answers = {
            q: verify(a, s["fit"]["evidence"]).text for q, a in s["draft"].get("screening_answers", {}).items()
        }
        return {
            "draft": verified.model_dump(),
            "steps": 1,
            "events": [
                {
                    "node": "verifier",
                    "removed": sum(c.status in ("unsupported", "partly_supported") for c in verified.claims),
                    "trace_id": s["trace_id"],
                }
            ],
        }

    async def critic(s):
        async def run():
            result = await generate("critic", {"job": s["spec"], "proposal": s["draft"]}, s["trace_id"])
            issues = []
            if not s["draft"]["text"]:
                issues.append("No safe content remains")
            if not any(c["status"] == "supported" for c in s["draft"]["claims"]):
                issues.append("No supported portfolio claim")
            raw = result["output"].get("issues", [])
            if isinstance(raw, list):
                issues.extend(str(x)[:300] for x in raw[:3])
            revision = min(2, s.get("revision", 0))
            return {
                "critique": Critique(passed=not issues, issues=issues, revision=revision).model_dump(),
                "revision": revision,
                "_usage": result,
            }

        return await observed("critic", s, run)

    def guard(s):
        verdict = compliance(s["draft"]["text"], s["fit"]["evidence"])
        exceeded = (
            s.get("tokens", 0) > config()["budgets"]["max_tokens_per_job"]
            or s.get("steps", 0) >= config()["budgets"]["max_graph_steps"]
        )
        if exceeded:
            return {"compliance": verdict.model_dump(), "status": "needs_attention", "error": "Run budget exceeded"}
        if not s["critique"]["passed"]:
            return {
                "compliance": verdict.model_dump(),
                "status": "needs_attention",
                "error": "Critic could not approve within revision limit",
            }
        return {"compliance": verdict.model_dump(), "status": "awaiting_approval" if verdict.allowed else "blocked"}

    def request(s):
        return {
            "idempotency_key": "proposal-" + s["trace_id"],
            "job_id": s["job_id"],
            "text": s["draft"]["text"],
            "amount": s["price"]["amount"],
            "screening_answers": s["draft"].get("screening_answers", {}),
            "approval_token": "",
            "dry_run": True,
            "trace_id": s["trace_id"],
        }

    async def preview(s):
        result = await gateway.call("approval", "submit_proposal", request=request(s))
        return {"preview": result}

    def approval(s):
        answer = Approval.model_validate(
            interrupt(
                {
                    "kind": "proposal",
                    "draft": s["draft"],
                    "evidence": s["fit"]["evidence"],
                    "risk": s["risk"],
                    "price": s["price"],
                    "preview": s["preview"],
                    "allowed_actions": ["approve", "edit", "reject"],
                }
            )
        )
        if answer.action == "reject":
            return {"approval": answer.model_dump(), "status": "rejected"}
        if answer.action == "edit":
            edited = answer.text or ""
            verdict = compliance(edited, s["fit"]["evidence"])
            if not verdict.allowed:
                return {
                    "approval": answer.model_dump(),
                    "compliance": verdict.model_dump(),
                    "status": "blocked",
                    "error": "Edited text failed grounding or policy checks",
                }
            d = verify(edited, s["fit"]["evidence"], s["draft"]["version"] + 1)
            d.screening_answers = s["draft"].get("screening_answers", {})
            return {"approval": answer.model_dump(), "draft": d.model_dump(), "status": "awaiting_approval"}
        # Exact preview binding makes edited or replayed authorization unusable elsewhere.
        grant = token(s["tenant"], "approved_write", ttl=86400, hash=s["preview"]["payload_hash"])
        return {"approval": answer.model_dump(), "approval_token": grant, "status": "approved"}

    async def dispatch(s):
        # Re-read every cited item at send time. Deleted evidence invalidates old approval.
        fresh = []
        for item in s["fit"]["evidence"]:
            try:
                fresh.append(await gateway.call("writer", "get_case_study", id=item["id"]))
            except ValueError:
                verdict = compliance(s["draft"]["text"], [])
                verdict.violations = ["Cited evidence is unavailable. Regenerate the proposal before approving again."]
                return {"status": "blocked", "compliance": verdict.model_dump(), "error": verdict.violations[0]}
        verdict = compliance(s["draft"]["text"], fresh)
        if not verdict.allowed:
            return {"status": "blocked", "compliance": verdict.model_dump()}
        req = request(s)
        req.update(dry_run=False, approval_token=s["approval_token"])
        result = await gateway.call("dispatch", "submit_proposal", request=req)
        return {
            "outcome": result,
            "status": "awaiting_platform_confirmation" if result.get("requires_platform_confirmation") else "submitted",
            "events": [{"node": "dispatch", "trace_id": s["trace_id"], "result": result}],
        }

    graph = StateGraph(BidState)
    for name, fn in [
        ("scout", scout),
        ("analyst", analyst),
        ("risk", risk),
        ("fit", fit),
        ("decision", decision),
        ("pricing", pricing),
        ("writer", writer),
        ("verifier", verifier),
        ("critic", critic),
        ("compliance", guard),
        ("preview", preview),
        ("approval", approval),
        ("dispatch", dispatch),
    ]:
        graph.add_node(name, fn)
    graph.add_edge(START, "scout")
    graph.add_conditional_edges(
        "scout", lambda s: [Send(node, s) for node in ("analyst", "risk", "fit")], ["analyst", "risk", "fit"]
    )
    graph.add_edge(["analyst", "risk", "fit"], "decision")
    graph.add_conditional_edges(
        "decision", lambda s: "pricing" if s["decision"]["action"] == "bid" else END, ["pricing", END]
    )
    graph.add_conditional_edges("pricing", lambda s: "writer" if s["price"]["viable"] else END, ["writer", END])
    graph.add_edge("writer", "verifier")
    graph.add_edge("verifier", "critic")
    graph.add_conditional_edges(
        "critic",
        lambda s: (
            "writer"
            if not s["critique"]["passed"] and s.get("revision", 0) < config()["budgets"]["max_revisions"]
            else "compliance"
        ),
        ["writer", "compliance"],
    )
    graph.add_conditional_edges(
        "compliance", lambda s: "preview" if s["status"] == "awaiting_approval" else END, ["preview", END]
    )
    graph.add_edge("preview", "approval")
    graph.add_conditional_edges(
        "approval",
        lambda s: (
            "dispatch" if s["status"] == "approved" else ("preview" if s["status"] == "awaiting_approval" else END)
        ),
        ["dispatch", "preview", END],
    )
    graph.add_edge("dispatch", END)
    from agent.memory.store import MemoryStore

    return graph.compile(checkpointer=checkpointer, store=MemoryStore())
