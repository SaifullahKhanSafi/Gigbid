from mcp_servers.contracts import BalanceOutput, HistoryOutput, JobOutput, JobsOutput, MessagesOutput, WriteOutput
from typing import Annotated
from pydantic import Field
from agent.handoffs import WriteRequest, MessageRequest
from core.settings import config
from core.security import tenant, decode, digest
from mcp_servers.common import server, http_app, READ, WRITE, rate_limit, audit_call

mcp = server("GigBid Marketplace", 8102)


def adapter():
    mode = config()["marketplace"]["mode"]
    if mode == "local_sim":
        from mcp_servers.marketplace.adapters.local_sim import LocalSimulator

        return LocalSimulator()
    if mode == "gigsim":
        from mcp_servers.marketplace.adapters.gigsim import GigSimAdapter

        return GigSimAdapter()
    if mode == "upwork":
        from mcp_servers.marketplace.adapters.upwork_live import UpworkAdapter

        return UpworkAdapter()
    raise ValueError("Unknown marketplace mode")


async def call(name, args, trace_id):
    rate_limit(tenant(), config()["marketplace"]["requests_per_minute"])
    result = await getattr(adapter(), name)(**args)
    audit_call(name, args, result, trace_id)
    return result


@mcp.tool(annotations=READ, structured_output=True)
async def search_jobs(
    query: str = "", limit: Annotated[int, Field(ge=1, le=100)] = 20, trace_id: str = "local"
) -> JobsOutput:
    """Search the configured marketplace feed. Read only; never spend Connects."""
    return await call("search_jobs", {"query": query, "limit": limit}, trace_id)


@mcp.tool(annotations=READ, structured_output=True)
async def get_job(job_id: str, trace_id: str = "local") -> JobOutput:
    """Load one known job ID, with original untrusted description and client reference."""
    return await call("get_job", {"job_id": job_id}, trace_id)


@mcp.tool(annotations=READ, structured_output=True)
async def get_client_history(client_id: str, trace_id: str = "local") -> HistoryOutput:
    """Read client spend, rating, verification and hiring history for risk/pricing."""
    return await call("get_client_history", {"client_id": client_id}, trace_id)


@mcp.tool(annotations=READ, structured_output=True)
async def get_connects_balance(trace_id: str = "local") -> BalanceOutput:
    """Read the authenticated user's Connects balance; no mutation."""
    return await call("get_connects_balance", {}, trace_id)


@mcp.tool(annotations=READ, structured_output=True)
async def list_messages(conversation_id: str, trace_id: str = "local") -> MessagesOutput:
    """Read only the authenticated user's client conversation."""
    return await call("list_messages", {"conversation_id": conversation_id}, trace_id)


async def write(name, request):
    data = request.model_dump()
    if config()["marketplace"]["mode"] == "upwork" and data["dry_run"]:
        canonical = dict(
            {k: v for k, v in data.items() if k not in ("approval_token", "dry_run", "trace_id")}, action=name
        )
        return {
            "dry_run": True,
            "payload": canonical,
            "payload_hash": digest(canonical),
            "connects_cost": None,
            "destination": "official_upwork_mcp",
            "requires_platform_confirmation": True,
            "note": "No live write called; cost must be confirmed from the official advertised tool.",
        }
    # Defense at the server boundary applies equally to official and local adapters.
    if not data["dry_run"]:
        expected = digest(
            dict({k: v for k, v in data.items() if k not in ("approval_token", "dry_run", "trace_id")}, action=name)
        )
        grant = decode(data["approval_token"], "approved_write")
        if grant["sub"] != tenant() or grant.get("hash") != expected:
            raise PermissionError("Approval content mismatch")
    return await call(name, {"payload": data}, data["trace_id"])


@mcp.tool(annotations=WRITE, structured_output=True)
async def create_proposal_draft(request: WriteRequest) -> WriteOutput:
    """Preview or create a proposal draft; mutation requires an exact-content human approval grant."""
    return await write("create_proposal_draft", request)


@mcp.tool(annotations=WRITE, structured_output=True)
async def submit_proposal(request: WriteRequest) -> WriteOutput:
    """Submit only a human-approved proposal. Idempotency key prevents duplicate Connects spend."""
    return await write("submit_proposal", request)


@mcp.tool(annotations=WRITE, structured_output=True)
async def send_message(request: MessageRequest) -> WriteOutput:
    """Send one approved client message. Preview is dry-run by default; never auto-send."""
    return await write("send_message", request)


app = http_app(mcp)
if __name__ == "__main__":
    import os

    if os.getenv("MCP_HTTP") == "1":
        import uvicorn

        uvicorn.run(
            app,
            host="127.0.0.1" if os.getenv("GIGBID_ENV") != "production" else "0.0.0.0",
            port=int(os.getenv("MCP_PORT", "8102")),
            access_log=False,
        )
    else:
        mcp.run()
