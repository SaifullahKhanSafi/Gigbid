"""Fail-closed official MCP adapter. Tool names are discovered and explicitly mapped."""

import json
import os
from langchain_mcp_adapters.client import MultiServerMCPClient
from core.security import tenant
from apps.api.auth.oauth_store import load_tokens
from jsonschema import validate

WRITE_ACTIONS = {"create_proposal_draft", "submit_proposal", "send_message"}


class UpworkAdapter:
    async def call(self, name, args):
        if set(args) == {"payload"}:
            args = args["payload"]
        creds = load_tokens(tenant(), "upwork")
        if not creds:
            raise PermissionError("Complete Upwork OAuth connection first")
        mapping_path = os.getenv("UPWORK_TOOL_MAP")
        if not mapping_path:
            raise RuntimeError("Discover official tools and configure UPWORK_TOOL_MAP before live use")
        mapping = json.loads(open(mapping_path, encoding="utf-8").read())
        remote = mapping[name]
        client = MultiServerMCPClient(
            {
                "upwork": {
                    "transport": "streamable_http",
                    "url": os.getenv("UPWORK_MCP_URL", "https://mcp.upwork.com/mcp"),
                    "headers": {"Authorization": "Bearer " + creds["access_token"]},
                }
            }
        )
        async with client.session("upwork") as session:
            discovered = await session.list_tools()
            tool = next((x for x in discovered.tools if x.name == remote["tool"]), None)
            if not tool:
                raise RuntimeError("Configured live tool is not advertised by Upwork")
            if name in WRITE_ACTIONS and not remote.get("draft_only"):
                raise PermissionError("Live writes require an explicitly verified draft-only tool")
            if name in WRITE_ACTIONS and not remote.get("supports_idempotency"):
                raise PermissionError("Live write idempotency must be verified before enabling it")
            argument_map = remote.get("arguments", {})
            mapped = {
                remote.get("arguments", {}).get(k, k): v
                for k, v in args.items()
                if k not in ("approval_token", "trace_id") and (not argument_map or k in argument_map)
            }
            validate(mapped, tool.inputSchema)
            result = await session.call_tool(tool.name, mapped)
            if result.isError:
                raise RuntimeError("Upwork tool returned an error")
            body = result.structuredContent or {"content": [x.model_dump() for x in result.content]}
            if name in WRITE_ACTIONS:
                return {
                    "action": name,
                    "status": "awaiting_platform_confirmation",
                    "requires_platform_confirmation": True,
                    "connects_spent": 0,
                    "remote_result": body,
                    "destination": "official_upwork_mcp",
                }
            output_map = remote.get("output_map")
            if output_map:
                normalized = {}
                for local, path in output_map.items():
                    value = body
                    for key in path.split("."):
                        value = value[key]
                    normalized[local] = value
                return normalized
            return body

    def __getattr__(self, name):
        async def invoke(*args, **kwargs):
            return await self.call(name, kwargs or (args[0] if len(args) == 1 and isinstance(args[0], dict) else {}))

        return invoke
