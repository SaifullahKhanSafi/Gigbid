import json
import uuid
import pytest
from mcp.shared.memory import create_connected_server_and_client_session
from core.security import tenant_context
from core.settings import ROOT
from mcp_servers.marketplace.server import mcp, app


@pytest.mark.asyncio
async def test_auth_and_write_without_grant():
    import httpx

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.post("/mcp", json={})).status_code == 401
    tenant_context.set("contract-" + uuid.uuid4().hex)
    async with create_connected_server_and_client_session(mcp) as client:
        result = await client.call_tool(
            "submit_proposal",
            {
                "request": {
                    "idempotency_key": "contract-write-00001",
                    "job_id": "demo-ml-0001",
                    "text": "I would test.",
                    "amount": 40,
                    "dry_run": False,
                }
            },
        )
        assert result.isError
        preview = await client.call_tool(
            "submit_proposal",
            {
                "request": {
                    "idempotency_key": "contract-write-00001",
                    "job_id": "demo-ml-0001",
                    "text": "I would test.",
                    "amount": 40,
                }
            },
        )
        assert not preview.isError and (preview.structuredContent or json.loads(preview.content[0].text))["dry_run"]


@pytest.mark.asyncio
async def test_schema_snapshot():
    from importlib import import_module

    snapshot = {}
    for name in ["portfolio", "marketplace", "workspace"]:
        server = import_module("mcp_servers." + name + ".server").mcp
        async with create_connected_server_and_client_session(server) as client:
            listed = await client.list_tools()
            snapshot[name] = [x.model_dump(mode="json", exclude_none=True) for x in listed.tools]
    expected = ROOT / "tests/contract/tool_schemas.json"
    assert expected.exists(), "Generate and review the MCP schema snapshot before running CI"
    assert snapshot == json.loads(expected.read_text())
