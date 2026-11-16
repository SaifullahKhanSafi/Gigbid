"""Repository reads use GitHub's official MCP server, not browser scraping or raw HTTP."""

import os
from langchain_mcp_adapters.client import MultiServerMCPClient
from core import db
from core.security import mask
from rag.retriever import reindex


async def ingest_repository(tenant, owner, repo, paths, metadata):
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN with minimal repository-read permissions is required")
    if len(paths) > 30 or any(".." in p.split("/") for p in paths):
        raise ValueError("Invalid repository path list")
    client = MultiServerMCPClient(
        {
            "github": {
                "transport": "streamable_http",
                "url": os.getenv("GITHUB_MCP_URL", "https://api.githubcopilot.com/mcp/"),
                "headers": {"Authorization": "Bearer " + token},
            }
        }
    )
    items = []
    async with client.session("github") as session:
        tools = await session.list_tools()
        if not any(t.name == "get_file_contents" for t in tools.tools):
            raise RuntimeError("GitHub get_file_contents tool unavailable; review its advertised schema")
        for path in paths:
            result = await session.call_tool("get_file_contents", {"owner": owner, "repo": repo, "path": path})
            if result.isError:
                raise RuntimeError("GitHub MCP read failed")
            # Retain tool text as evidence, with source provenance; no automatic claims of success.
            text = "\n".join(getattr(b, "text", "") for b in result.content)
            import hashlib

            item = dict(
                metadata,
                id=hashlib.sha256((owner + repo + path + text).encode()).hexdigest()[:24],
                title=repo + "/" + path,
                text=mask(text),
                source=f"https://github.com/{owner}/{repo}/blob/HEAD/{path}",
                approved_claims=[],
                synthetic=False,
                provenance="GitHub official MCP get_file_contents; user-selected repository",
            )
            db.put(tenant, "evidence", item["id"], item)
            items.append(item)
    reindex(tenant)
    return items
