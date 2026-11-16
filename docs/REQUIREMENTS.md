# Requirement traceability

Status is local evidence, not a claim of full grading compliance. **External** means missing instructor/account/deployment inputs. **Partial** identifies a concrete implementation gap.

| Requirement | Implementation/evidence | Status |
|---|---|---|
| R1 one marketplace port | `agent/marketplace_port.py`, three adapter implementations | Local tested; official adapters external |
| R2 own MCP + third party | Three SDK servers; GitHub/Upwork clients | Own servers tested; third-party authorization external |
| R3 handwritten parallel graph | Send fanout/join in bid graph | Tested |
| R4 UI interrupts | Approval/edit/reject, checkpoint resume, server grants | Python and browser tested |
| R5 grounded claims | Conservative exact-fact/quotation verifier, dispatch re-read | Tested; semantic paraphrase recall limited |
| R6 measured RAG choice | Six variants, retrieval/ablation results, V1 config | Measured on synthetic dev only |
| R7 promotion memory | LangGraph BaseStore, style/outcome rules and deletion | Tested; local outcomes synthetic |
| R8 observability/budgets | Durable events/audit; OTLP spans; measured runners | Local measured; Phoenix public links external |
| R9 platform respect | No scraping, injection/PII checks, auth and rate limits | Local tested; model-level ASR partial |
| R10 deployment | Local app, Compose, Render reference | Local works; Compose daemon/public URL external |
| A1 Portfolio | search/get/list tools, resources, prompt | Implemented/tested |
| A2 Marketplace | constrained write schemas, annotations, dry-run/grants, receipt/wallet transaction | Local tested; official contract external |
| A3 Workspace | slots, hold, email draft local mock | Implemented; atomic race tests partial |
| A4 live OAuth | SDK PKCE/discovery, encrypted storage, draft-only fail-closed mapping | Wired; actual flow external |
| A5 third-party trust | official Upwork and GitHub configs/trust rationale | Connected-session verification external |
| A6 discipline | allowlists, timeout/retry, unavailable states | Tested locally |
| A7 Inspector/schema | in-memory MCP tests and schema snapshot | Tests done; actual Inspector screenshots pending |
| R&D A 40 tasks | fine/coarse/rewritten JSON-selection study | Measured; not a native tool-call study |
| B1 ingestion | PDF/Markdown/source/review/proposal loaders, UI incremental index | Tested generally; GitHub token external |
| B2 retrieval | V0,V1,V2,V3,V4,V8 | Implemented/measured |
| B3 verification | split/status/remove, safety probes | Measured; conservative verifier can over-remove |
| B4 metrics | retrieval/decision/latency per persona | Local measured; official outcomes/human quality external |
| B5 ablation | paired additions and breakdowns | Measured; no full factorial study |
| C1/C3 graphs/handoffs | two typed graphs, Pydantic handoffs | Tested |
| C2 state/trace/memory | distinct stores and namespaces | Implemented/tested |
| C4 loops/budgets | bounded revisions, recursion/token limits, needs attention | Tested locally; exact token reservations partial |
| C5 approval | dry-run payload/risk/price/evidence; edits rechecked | Browser tested |
| R&D C 50 jobs | ReAct, prebuilt supervisor, handwritten uniform-model comparison | Measured; initial supervisor schema bug retained separately |
| D screens | all named routes, responsive UI, evidence details | Local implemented; several marketplace event states need official service |
| D typed API/SSE | generated TS schema, durable stream replay | Build/browser tested |
| D five E2E tests | six tests including required flows and mobile | Passed locally with explicit model doubles |
| E1 workers | separate local queue worker; Arq/Redis schedule | Local tested; Redis deployment unverified |
| E2 CI | unit/schema/browser jobs and smoke eval gates | Configured; remote CI execution pending push |
| E3 tracing | trace IDs and audit, Phoenix Compose exporter | Local audit tested; hosted tracer external |
| E4 safety | tenant auth/encryption/masking, detector probes | Tested locally; no claim of complete jailbreak protection |
| E5 budgets | declared config, real local timings/tokens | Measured local; hidden test external |
| E6 packaging | Dockerfiles/Compose/Render config | Compose syntax checked; engine/deployment external |
| X1 agency | per-persona coverage routing experiment | Integrated and locally tested; synthetic coverage measured |
| Portfolio deliverables | report/write-up/demo sources and local artifacts | Publication/account-dependent items external |
| Official policy change | configuration-driven policy plus local rehearsal | Official November 2 update absent |
| Calibration/panel | import script and blank human label sheets | Must be completed by real humans |
