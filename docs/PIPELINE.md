# Assignment execution pipeline

Source of requirements: the 14-page AI-4016 GigBid assignment supplied by the user. The example ZIP was inspected as reference only; its source and sample records are not copied into this implementation.

## Dependency order and acceptance gates

1. **Requirements and assets.** Map R1-R10 and A1-E6; preserve official assets if supplied; record missing inputs and licenses. Gate: every requirement has a test or an explicit external dependency.
2. **Data.** Download TA-approved sources through Kaggle APIs; retain checksums and license metadata; normalize, remove PII, deduplicate, split before indexing. Generate labelled synthetic personas, histories and conversations separately. Gate: provenance on every record, no evaluation labels exposed to agents.
3. **MCP boundary.** Implement Portfolio, Marketplace and Workspace with SDK schemas, annotations, authentication, tenant isolation, dry runs, write authorization and idempotency. Gate: MCP contract, unauthorized-write and retry tests.
4. **Retrieval.** Implement V0, V1, V2, V3, V4 and V8. Declare hypotheses before measurement, evaluate by persona and requirement count, then select the deployed variant. Gate: reproducible Recall@5/MRR/nDCG@10 and claim-verification results.
5. **Durable agents.** Implement parallel Send branches, bounded critique, policy checks, interrupts, approval-bound writes, budgets, memory promotion and crash recovery. Gate: edit/reject/restart tests and no send without approval.
6. **Product.** React/TypeScript UI, FastAPI auth and typed contract, background workers, durable SSE replay, all required screens. Gate: browser onboarding/approval/rejection/edit/degraded tests plus mobile inspection.
7. **Experiments.** Tool granularity (40 tasks), two local open-model configurations, single/ReAct-supervisor/hand-built comparison (50 jobs), ablations, attacks, X1 agency routing, calibrated judge and blind panel. Gate: measured raw records; unavailable official/human results remain null, never estimated.
8. **Operations.** Compose, CI gates, traces, rate limits, policy-change rehearsal, documentation. Gate: tested local startup; separately verify public deployment when hosting access exists.
9. **Deliverables.** <=10-page R&D PDF, technical write-up, demo assets, installable MCP package, submission checklist and viva guide. Gate: artifacts distinguish executed, unexecuted, synthetic and externally blocked work.

## Known external dependencies at intake

- The example ZIP has no official GigSim implementation/URL, full persona corpora, dev labels, hidden set or November 2 policy update.
- Kaggle public dataset endpoints returned HTTP 404 on 2026-11-15. No Kaggle records or licenses have yet been verified locally.
- Public GitHub/hosting and Upwork/GitHub OAuth credentials have not been supplied.
- Human calibration labels, blind panel ratings, final platform confirmation and submission require the student's participation.
- The assignment's stated deadline is 2026-11-12 23:59 PKT, before this work started. No timestamps or commit history will be backdated.

Use `docs/REQUIREMENTS.md`, generated experiment results, and `docs/STATUS.md` to audit completion.
