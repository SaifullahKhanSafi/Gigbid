"""Least-privilege MCP gateway. Nodes receive this gateway, not storage or API clients."""

import asyncio
from contextlib import AsyncExitStack
import json
import os
import sys
from langchain_mcp_adapters.client import MultiServerMCPClient
from core.settings import ROOT
from core.security import token
from core.telemetry import span

ALLOWLISTS = {
    "scout": {"search_jobs", "get_job"},
    "analyst": set(),
    "risk": {"get_client_history"},
    "fit": {"search_evidence", "rank_team", "get_case_study", "list_skills"},
    "pricing": {"get_connects_balance", "get_client_history"},
    "writer": {"get_case_study"},
    "critic": {"get_case_study"},
    "approval": {"submit_proposal", "create_proposal_draft", "send_message"},
    "dispatch": {"submit_proposal", "create_proposal_draft", "send_message"},
    "liaison": {"list_messages", "free_slots"},
}
OWNER = {
    name: server
    for server, names in {
        "portfolio": ["search_evidence", "rank_team", "get_case_study", "list_skills"],
        "marketplace": [
            "search_jobs",
            "get_job",
            "get_client_history",
            "get_connects_balance",
            "list_messages",
            "create_proposal_draft",
            "submit_proposal",
            "send_message",
        ],
        "workspace": ["free_slots", "create_interview_hold", "create_email_draft"],
    }.items()
    for name in names
}


class MarketplaceUnavailable(RuntimeError):
    pass


class ToolGateway:
    def __init__(self, tenant, trace_id):
        self.tenant = tenant
        self.trace_id = trace_id
        self.stack = AsyncExitStack()
        self.sessions = {}
        self.tools = {}

    async def __aenter__(self):
        configs = {}
        for server in ("portfolio", "marketplace", "workspace"):
            if os.getenv("GIGBID_MCP_TRANSPORT", "stdio") == "http":
                configs[server] = {
                    "transport": "streamable_http",
                    "url": os.environ[server.upper() + "_MCP_URL"],
                    "headers": {"Authorization": "Bearer " + token(self.tenant, "mcp", ttl=86400)},
                }
            else:
                configs[server] = {
                    "transport": "stdio",
                    "command": sys.executable,
                    "args": ["-m", f"mcp_servers.{server}.server"],
                    "cwd": str(ROOT),
                    "env": dict(os.environ, GIGBID_TENANT=self.tenant),
                }
        self.client = MultiServerMCPClient(configs)
        # Enter and exit SDK task-group contexts in this same owning task.
        # Lazy entry inside parallel LangGraph nodes violates AnyIO cancel-scope ownership.
        try:
            for owner in configs:
                self.sessions[owner] = await self.stack.enter_async_context(self.client.session(owner))
        except BaseException:
            await self.stack.aclose()
            raise
        return self

    async def __aexit__(self, *exc):
        return await self.stack.__aexit__(*exc)

    async def session(self, owner):
        if owner not in self.sessions:
            session = await self.stack.enter_async_context(self.client.session(owner))
            self.sessions[owner] = session
        return self.sessions[owner]

    async def call(self, role, name, **args):
        if name not in ALLOWLISTS.get(role, set()):
            raise PermissionError(f"{role} cannot call {name}")
        if name in ("submit_proposal", "create_proposal_draft", "send_message"):
            args["request"] = dict(args["request"], trace_id=self.trace_id)
        else:
            args["trace_id"] = self.trace_id
        owner = OWNER[name]
        for attempt in range(3):
            try:
                with span("mcp." + name, self.trace_id, role=role, server=owner):
                    session = await self.session(owner)
                    result = await asyncio.wait_for(
                        session.call_tool(name, args), timeout=90 if owner == "portfolio" else 25
                    )
                    if result.isError:
                        details = " ".join(getattr(c, "text", "") for c in result.content)
                        if any(
                            word in details.lower()
                            for word in [
                                "approval",
                                "permission",
                                "unknown job",
                                "idempotency",
                                "connects limit",
                                "rate limit",
                                "invalid",
                                "evidence not found",
                            ]
                        ):
                            raise ValueError(details[:600])
                        raise RuntimeError(details[:600])
                    if result.structuredContent is not None:
                        return result.structuredContent
                    for block in result.content:
                        if getattr(block, "type", "") == "text":
                            return json.loads(block.text)
                    return {}
            except (PermissionError, ValueError):
                raise
            except Exception as e:
                if attempt == 2:
                    raise MarketplaceUnavailable(f"{owner} MCP unavailable; work is queued for retry") from e
                await asyncio.sleep(0.5 * 2**attempt)
