# ADR 004: Keep local execution independent of hosting

The user's GPU and existing D: open models make a local end-to-end app practical. Shared authenticated MCP services avoid repeated cold imports. SQLite checkpoints and queue leases provide a development fallback; Compose uses Postgres/Redis. Cloud deployment is separate because Render cannot call this laptop's localhost and free service persistence is insufficient for reliable pending approvals.
