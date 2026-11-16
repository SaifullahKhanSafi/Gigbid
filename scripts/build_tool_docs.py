import json
from core.settings import ROOT
from importlib import import_module


def main():
    rows = [
        "# MCP tool inventory",
        "",
        "HTTP endpoints require a tenant-scoped bearer JWT issued by GigBid; stdio is an owner-selected local process. Write grants are separate, exact-content approvals. All write tools are non-destructive draft/submit operations with stable idempotency keys. The local mock spends only fictional Connects.",
        "",
        "| Tool | Owner | Access | readOnly / destructive / idempotent | Auth |",
        "|---|---|---|---|---|",
    ]
    schemas = json.loads((ROOT / "tests/contract/tool_schemas.json").read_text())
    outputs = {}
    for owner, tools in schemas.items():
        module = import_module("mcp_servers." + owner + ".server")
        for tool in tools:
            a = tool["annotations"]
            is_read = a.get("readOnlyHint", False)
            rows.append(
                f"| `{tool['name']}` | {owner} | {'read' if is_read else 'write/dry-run'} | {a.get('readOnlyHint')} / {a.get('destructiveHint')} / {a.get('idempotentHint')} | Bearer tenant; "
                + ("no write grant" if is_read else "exact-content grant for mutation")
                + " |"
            )
            outputs[owner + "." + tool["name"]] = module.mcp._tool_manager.get_tool(
                tool["name"]
            ).fn_metadata.output_schema
    rows.extend(
        [
            "",
            "## Contracts and server surfaces",
            "",
            "Input signatures and annotations are frozen in `tests/contract/tool_schemas.json`. Typed Pydantic output contracts are saved in `declared_output_schemas.json`; protocol negotiation may affect whether outputSchema appears on the wire. Unit/in-memory MCP tests validate actual tool calls, and the official Inspector is used for screenshots. Portfolio resources and prompt templates are in its server module.",
            "",
            "Portfolio evidence carries type/source/date/outcome and synthetic provenance. rank_team requires the user to enable agency mode. Workspace slots/holds/email drafts are a local mock. Marketplace idempotency receipts and Connects debits commit in the same tenant transaction. Dry-run never calls a live write.",
            "",
            "## Third-party trust and limitations",
            "",
            "- Official Upwork MCP (`https://mcp.upwork.com/mcp`): first-party account authority, OAuth 2.1, minimal granted scopes; tool names and draft-only/idempotency behavior must be verified before enabling a mapped write. Actual authorization is not yet tested. [Official description](https://www.upwork.com/ai/mcp).",
            "- Official GitHub MCP (`https://api.githubcopilot.com/mcp/`): first-party repository read capabilities using a minimally scoped token; repository text remains untrusted and is never executed. Actual token/session verification is pending. [Official server](https://github.com/github/github-mcp-server).",
            "",
            "Agents receive only named allowlists from agent/mcp_client.py. Timeout/retry behavior is bounded; mutation retries keep the same idempotency key. Marketplace failures become queued retry/needs attention. No node receives the token store or a raw marketplace HTTP client.",
        ]
    )
    (ROOT / "docs/TOOLS.md").write_text("\n".join(rows) + "\n")
    (ROOT / "tests/contract/declared_output_schemas.json").write_text(json.dumps(outputs, indent=2) + "\n")
    print("Generated tool inventory and declared output schemas.")


if __name__ == "__main__":
    main()
