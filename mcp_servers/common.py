import time
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from starlette.responses import JSONResponse
from core.security import decode, tenant_context, tenant
from core import db

READ = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)
WRITE = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=True)


def server(name, port):
    return FastMCP(name, host="0.0.0.0", port=port, stateless_http=True, json_response=True, log_level="WARNING")


class BearerAuth:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = dict(scope["headers"])
        try:
            auth = headers.get(b"authorization", b"").decode()
            payload = decode(auth.removeprefix("Bearer "), "mcp")
            user = payload["sub"]
        except Exception:
            return await JSONResponse({"error": "Bearer authentication required"}, status_code=401)(
                scope, receive, send
            )
        marker = tenant_context.set(user)
        try:
            await self.app(scope, receive, send)
        finally:
            tenant_context.reset(marker)


def http_app(mcp):
    return BearerAuth(mcp.streamable_http_app())


def audit_call(tool, args, result, trace_id):
    db.audit(tenant(), trace_id, {"tool": tool, "arguments": args, "result": result})


def rate_limit(user, limit=18):
    # A shared DB window survives restarts; enforced at the marketplace boundary.
    from mcp_servers.marketplace.adapters.local_sim import lock

    window = str(int(time.time() // 60))
    with db.connection() as c:
        lock(c, "rate:" + user)
        row = db.get(user, "rate", "marketplace", c) or {"window": window, "count": 0}
        if row["window"] != window:
            row = {"window": window, "count": 0}
        if row["count"] >= limit:
            raise RuntimeError("Rate limit reached; retry after the next minute")
        row["count"] += 1
        db.put(user, "rate", "marketplace", row, c)
