import asyncio
import json
from importlib import import_module
from mcp.shared.memory import create_connected_server_and_client_session
from core.settings import ROOT


async def main():
    snapshot = {}
    for name in ["portfolio", "marketplace", "workspace"]:
        server = import_module("mcp_servers." + name + ".server").mcp
        async with create_connected_server_and_client_session(server) as client:
            result = await client.list_tools()
            snapshot[name] = [x.model_dump(mode="json", exclude_none=True) for x in result.tools]
    (ROOT / "tests/contract/tool_schemas.json").write_text(json.dumps(snapshot, indent=2) + "\n")


if __name__ == "__main__":
    asyncio.run(main())
