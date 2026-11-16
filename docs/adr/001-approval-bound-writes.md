# ADR 001: Bind approval to exact content at the MCP boundary

An interrupted graph alone does not protect a tool endpoint. A short-lived server-signed grant binds tenant, action and canonical payload hash. Every non-dry write validates it; an atomic receipt binds idempotency key to content. Edits invalidate the old preview and require a new interrupt. Send-time evidence revalidation handles deletions after approval. This is more complex than a boolean approved flag but makes replay and tampering reviewable.
