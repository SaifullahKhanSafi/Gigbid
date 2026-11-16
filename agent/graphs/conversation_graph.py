from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt
from agent.state import ConversationState
from agent.handoffs import Approval
from agent.nodes.logic import assess_risk, compliance
from core.security import token


def build_conversation_graph(gateway, checkpointer):
    async def liaison(s):
        messages = await gateway.call("liaison", "list_messages", conversation_id=s["conversation_id"])
        latest = next((m for m in messages["messages"] if m.get("sender") == "client"), None)
        if not latest:
            return {"messages": [], "status": "empty", "intent": "none"}
        text = latest["text"]
        risk = assess_risk(text, {})
        if risk.scam or risk.injection:
            return {"messages": messages["messages"], "intent": "scam_signal", "status": "blocked"}
        intent = (
            "interview"
            if "interview" in text.lower()
            else ("negotiation" if any(x in text.lower() for x in ["rate", "price", "budget"]) else "question")
        )
        slots = (await gateway.call("liaison", "free_slots", days=3))["slots"] if intent == "interview" else []
        draft = "I would validate a small slice against agreed acceptance criteria first. Could you share the sample inputs?"
        if slots:
            draft += "\nAvailability: " + ", ".join(x["start"] for x in slots) + " (UTC, tentative local mock)."
        if intent == "negotiation":
            draft = "Could you confirm the reduced scope? I would keep the agreed rate floor and discuss deliverables before changing the price."
        return {
            "messages": messages["messages"],
            "intent": intent,
            "slots": slots,
            "draft": draft,
            "status": "awaiting_approval",
            "events": [{"node": "liaison", "trace_id": s["trace_id"]}],
        }

    async def preview(s):
        request = {
            "idempotency_key": "message-" + s["trace_id"],
            "conversation_id": s["conversation_id"],
            "text": s["draft"],
            "dry_run": True,
            "approval_token": "",
        }
        return {"preview": await gateway.call("approval", "send_message", request=request)}

    async def approve(s):
        answer = Approval.model_validate(
            interrupt({"kind": "message", "draft": s["draft"], "slots": s.get("slots", []), "preview": s["preview"]})
        )
        if answer.action == "reject":
            return {"approval": answer.model_dump(), "status": "rejected"}
        if answer.action == "edit":
            return {"approval": answer.model_dump(), "draft": answer.text or "", "status": "edited"}
        verdict = compliance(s["draft"], [])
        if not verdict.allowed:
            return {"status": "blocked"}
        return {
            "approval": answer.model_dump(),
            "approval_token": token(s["tenant"], "approved_write", ttl=86400, hash=s["preview"]["payload_hash"]),
            "status": "approved",
        }

    async def send(s):
        result = await gateway.call(
            "dispatch",
            "send_message",
            request={
                "idempotency_key": "message-" + s["trace_id"],
                "conversation_id": s["conversation_id"],
                "text": s["draft"],
                "dry_run": False,
                "approval_token": s["approval_token"],
            },
        )
        return {
            "status": "awaiting_platform_confirmation" if result.get("requires_platform_confirmation") else "sent",
            "outcome": result,
            "events": [{"node": "send_message", "trace_id": s["trace_id"]}],
        }

    graph = StateGraph(ConversationState)
    graph.add_node("liaison", liaison)
    graph.add_node("preview", preview)
    graph.add_node("approval", approve)
    graph.add_node("send", send)
    graph.add_edge(START, "liaison")
    graph.add_conditional_edges(
        "liaison", lambda s: "preview" if s["status"] == "awaiting_approval" else END, ["preview", END]
    )
    graph.add_edge("preview", "approval")
    graph.add_conditional_edges(
        "approval",
        lambda s: "send" if s["status"] == "approved" else ("preview" if s["status"] == "edited" else END),
        ["send", "preview", END],
    )
    graph.add_edge("send", END)
    from agent.memory.store import MemoryStore

    return graph.compile(checkpointer=checkpointer, store=MemoryStore())
