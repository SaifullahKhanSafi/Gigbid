# MCP tool inventory

HTTP endpoints require a tenant-scoped bearer JWT issued by GigBid; stdio is an owner-selected local process. Write grants are separate, exact-content approvals. All write tools are non-destructive draft/submit operations with stable idempotency keys. The local mock spends only fictional Connects.

| Tool | Owner | Access | readOnly / destructive / idempotent | Auth |
|---|---|---|---|---|
| `search_evidence` | portfolio | read | True / False / True | Bearer tenant; no write grant |
| `rank_team` | portfolio | read | True / False / True | Bearer tenant; no write grant |
| `get_case_study` | portfolio | read | True / False / True | Bearer tenant; no write grant |
| `list_skills` | portfolio | read | True / False / True | Bearer tenant; no write grant |
| `search_jobs` | marketplace | read | True / False / True | Bearer tenant; no write grant |
| `get_job` | marketplace | read | True / False / True | Bearer tenant; no write grant |
| `get_client_history` | marketplace | read | True / False / True | Bearer tenant; no write grant |
| `get_connects_balance` | marketplace | read | True / False / True | Bearer tenant; no write grant |
| `list_messages` | marketplace | read | True / False / True | Bearer tenant; no write grant |
| `create_proposal_draft` | marketplace | write/dry-run | False / False / True | Bearer tenant; exact-content grant for mutation |
| `submit_proposal` | marketplace | write/dry-run | False / False / True | Bearer tenant; exact-content grant for mutation |
| `send_message` | marketplace | write/dry-run | False / False / True | Bearer tenant; exact-content grant for mutation |
| `free_slots` | workspace | read | True / False / True | Bearer tenant; no write grant |
| `create_interview_hold` | workspace | write/dry-run | False / False / True | Bearer tenant; exact-content grant for mutation |
| `create_email_draft` | workspace | write/dry-run | False / False / True | Bearer tenant; exact-content grant for mutation |

## Contracts and server surfaces

Input signatures and annotations are frozen in `tests/contract/tool_schemas.json`. Typed Pydantic output contracts are saved in `declared_output_schemas.json`; protocol negotiation may affect whether outputSchema appears on the wire. Unit/in-memory MCP tests validate actual tool calls, and the official Inspector is used for screenshots. Portfolio resources and prompt templates are in its server module.

Portfolio evidence carries type/source/date/outcome and synthetic provenance. rank_team requires the user to enable agency mode. Workspace slots/holds/email drafts are a local mock. Marketplace idempotency receipts and Connects debits commit in the same tenant transaction. Dry-run never calls a live write.

## Third-party trust and limitations

- Official Upwork MCP (`https://mcp.upwork.com/mcp`): first-party account authority, OAuth 2.1, minimal granted scopes; tool names and draft-only/idempotency behavior must be verified before enabling a mapped write. Actual authorization is not yet tested. [Official description](https://www.upwork.com/ai/mcp).
- Official GitHub MCP (`https://api.githubcopilot.com/mcp/`): first-party repository read capabilities using a minimally scoped token; repository text remains untrusted and is never executed. Actual token/session verification is pending. [Official server](https://github.com/github/github-mcp-server).

Agents receive only named allowlists from agent/mcp_client.py. Timeout/retry behavior is bounded; mutation retries keep the same idempotency key. Marketplace failures become queued retry/needs attention. No node receives the token store or a raw marketplace HTTP client.
