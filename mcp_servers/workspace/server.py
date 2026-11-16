from mcp_servers.contracts import SlotsOutput, WorkspaceDraftOutput
from datetime import datetime, timedelta, timezone
from core import db
from core.security import tenant, decode, digest
from mcp_servers.common import server, http_app, READ, WRITE, audit_call

mcp = server("GigBid Workspace (local mock)", 8103)


@mcp.tool(annotations=READ, structured_output=True)
def free_slots(days: int = 3, trace_id: str = "local") -> SlotsOutput:
    """Return fictional calendar availability in UTC; this local mock is not a real calendar."""
    if not 1 <= days <= 14:
        raise ValueError("days must be between 1 and 14")
    start = datetime.now(timezone.utc).replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(days=1)
    holds = db.scan(tenant(), "calendar_hold")
    blocked = {x["start"] for x in holds}
    result = {
        "slots": [
            {"start": (start + timedelta(days=d)).isoformat(), "minutes": 30, "tentative": True}
            for d in range(days)
            if (start + timedelta(days=d)).isoformat() not in blocked
        ],
        "synthetic": True,
        "timezone": "UTC",
    }
    audit_call("free_slots", {"days": days}, result, trace_id)
    return result


def draft_write(kind, text, key, approval_token, dry_run, trace_id):
    content = {"kind": kind, "text": text, "idempotency_key": key}
    hash_value = digest(content)
    if dry_run:
        return {"dry_run": True, "payload": content, "payload_hash": hash_value, "cost": 0}
    grant = decode(approval_token, "approved_write")
    if grant["sub"] != tenant() or grant.get("hash") != hash_value:
        raise PermissionError("Human approval required")
    old = db.get(tenant(), kind, key)
    if old and old["payload_hash"] != hash_value:
        raise ValueError("Idempotency key content conflict")
    result = old or dict(content, payload_hash=hash_value, synthetic=True)
    db.put(tenant(), kind, key, result)
    audit_call(kind, content, result, trace_id)
    return result


@mcp.tool(annotations=WRITE, structured_output=True)
def create_interview_hold(
    start: str, idempotency_key: str, approval_token: str = "", dry_run: bool = True, trace_id: str = "local"
) -> WorkspaceDraftOutput:
    """Preview or create an approved tentative interview hold in the local mock calendar."""
    datetime.fromisoformat(start)
    result = draft_write("calendar_hold", start, idempotency_key, approval_token, dry_run, trace_id)
    if not dry_run:
        result["start"] = start
        db.put(tenant(), "calendar_hold", idempotency_key, result)
    return result


@mcp.tool(annotations=WRITE, structured_output=True)
def create_email_draft(
    text: str, idempotency_key: str, approval_token: str = "", dry_run: bool = True, trace_id: str = "local"
) -> WorkspaceDraftOutput:
    """Create an approved local email draft, never deliver an email."""
    if not 1 <= len(text) <= 12000:
        raise ValueError("Invalid draft length")
    return draft_write("email_draft", text, idempotency_key, approval_token, dry_run, trace_id)


app = http_app(mcp)
if __name__ == "__main__":
    import os

    if os.getenv("MCP_HTTP") == "1":
        import uvicorn

        uvicorn.run(
            app,
            host="127.0.0.1" if os.getenv("GIGBID_ENV") != "production" else "0.0.0.0",
            port=int(os.getenv("MCP_PORT", "8103")),
            access_log=False,
        )
    else:
        mcp.run()
