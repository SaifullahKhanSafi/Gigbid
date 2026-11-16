from contextlib import asynccontextmanager
from types import SimpleNamespace
import json
import pytest
from core.security import tenant_context
from mcp_servers.marketplace.adapters.upwork_live import UpworkAdapter


@pytest.mark.asyncio
async def test_logical_submit_maps_only_to_verified_draft_tool(tmp_path, monkeypatch):
    tenant_context.set("upwork-contract-user")
    path = tmp_path / "tools.json"
    mapping = {
        "submit_proposal": {
            "tool": "verified_draft_tool",
            "draft_only": True,
            "supports_idempotency": True,
            "arguments": {"job_id": "job", "text": "letter", "idempotency_key": "key"},
        }
    }
    path.write_text(json.dumps(mapping))
    monkeypatch.setenv("UPWORK_TOOL_MAP", str(path))
    monkeypatch.setattr(
        "mcp_servers.marketplace.adapters.upwork_live.load_tokens", lambda *args: {"access_token": "test-token"}
    )
    calls = []

    class Session:
        async def list_tools(self):
            return SimpleNamespace(
                tools=[
                    SimpleNamespace(
                        name="verified_draft_tool",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "job": {"type": "string"},
                                "letter": {"type": "string"},
                                "key": {"type": "string"},
                            },
                            "required": ["job", "letter", "key"],
                            "additionalProperties": False,
                        },
                    )
                ]
            )

        async def call_tool(self, name, args):
            calls.append((name, args))
            return SimpleNamespace(isError=False, structuredContent={"draft_id": "d1"})

    class Client:
        def __init__(self, *args, **kwargs):
            pass

        @asynccontextmanager
        async def session(self, *args):
            yield Session()

    monkeypatch.setattr("mcp_servers.marketplace.adapters.upwork_live.MultiServerMCPClient", Client)
    result = await UpworkAdapter().submit_proposal(
        payload={
            "job_id": "job1",
            "text": "I would test.",
            "idempotency_key": "key123",
            "dry_run": False,
            "approval_token": "not-forwarded",
            "trace_id": "trace",
        }
    )
    assert result["requires_platform_confirmation"] and result["connects_spent"] == 0
    assert calls == [("verified_draft_tool", {"job": "job1", "letter": "I would test.", "key": "key123"})]
    mapping["submit_proposal"]["draft_only"] = False
    path.write_text(json.dumps(mapping))
    with pytest.raises(Exception):
        await UpworkAdapter().submit_proposal(payload={"job_id": "job1", "text": "test", "idempotency_key": "key123"})
    assert len(calls) == 1
