# Operations runbook

## This machine

The prepared project uses Python in the parent `.venv`, Ollama at `http://127.0.0.1:11436`, and model storage `D:\ollama\models`. The extra service avoids changing the user's existing Ollama configuration. If Ollama is not running:

```powershell
$env:OLLAMA_MODELS='D:\ollama\models'
$env:OLLAMA_HOST='127.0.0.1:11436'
ollama serve
```

In another terminal in `gigbid`, run `..\.venv\Scripts\python.exe -m scripts.start_local`. Open `http://127.0.0.1:8000`. Login credentials for the seeded reviewer are private in `runtime/reviewer-login.txt`; new users may register in the UI. Changing the secret invalidates sessions/grants; do not rotate it while approvals are pending.

The launcher starts local authenticated MCP HTTP services on loopback ports 8101-8103, a separate queue worker and the API. Its PID manifest is `runtime/processes.json`; logs are under `runtime/logs`. Ctrl+C terminates the processes it owns. Avoid starting a second launcher on those ports. The local durable queue is a fallback for machines without Redis; scheduled scouting requires the Arq worker in Compose.

## Fresh setup

Use Python 3.12 and Node 22. Create a venv, install PyTorch for your available hardware, then `pip install '.[dev]'`. Copy `.env.example` to `.env`. Generate `GIGBID_SECRET` with `secrets.token_hex(32)` and `OAUTH_ENCRYPTION_KEY` with `Fernet.generate_key()`. Never commit them. Seed data, install/build `apps/web`, then start the launcher. Download open models with Ollama, not through an unofficial mirror. The model downloader verifies official blob checksums.

Run `python -m scripts.export_openapi` and `npm run generate:api --prefix apps/web` after API changes. Do not hand-edit the generated schema. Run Python tests, frontend build and browser tests after changes to approval semantics. The browser test server has separate data and deterministic model doubles; it does not change live user records.

## Recovery, rate limits and approval

Marketplace reads/writes are limited per user below the assignment's illustrative limit; configure the actual limit from the official service when supplied. The gateway has timeouts and bounded exponential retries. Writes reuse a stable idempotency key. A reused key with different content is rejected. Local writes lock the tenant's wallet and commit proposal, receipt and Connects debit atomically.

Worker queue leases recover expired tasks. LangGraph checkpoints preserve pending interrupts. Retry resumes the saved graph; it does not create a new submission. A failure after the external transaction but before a checkpoint replays the same action against the stored receipt. Queue retry limits eventually surface needs-attention rather than retry forever. Production Arq errors/retry semantics and the actual instructor adapter still need deployment testing.

If Marketplace MCP is unavailable, the health banner explains that work is saved, and affected runs show queued-retry or needs-attention with a retry action. Do not bypass the approval/token checks to recover. If cited evidence is deleted, send-time revalidation blocks the proposal. If a budget or Critic limit is reached, inspect the trace and correct the draft/configuration.

Saved searches poll every four hours. This conservative interval is intended for a freelancer's review cadence, not feed scraping. No website scraping, browser cookies or browser automation is used for live marketplace access. Public job data is downloaded from the TA's licensed Kaggle archive.

## Compose and Render

Compose defines Postgres, Redis, Qdrant, Ollama, Phoenix, web/API, worker, MCP services and a marked local fixture. Set a production secret and change the example database password before exposing it. Model initialization may take time. Local CUDA can be enabled with a working NVIDIA container runtime and `gpus: all`. The current host's Docker daemon was unavailable, so Compose startup is unverified; configuration validation and local service tests are separate checks.

`infra/render.yaml` is a reference Blueprint, not a deployed service. Render supports web services and background workers, with managed Postgres and Key Value. A reliable version needs paid always-on worker capacity and persistent data. Free web services sleep, local files disappear on restart/spin-down, and free Postgres expires. Do not host pending approvals/checkpoints only on ephemeral SQLite. A public cloud app cannot reach localhost on this laptop. Supply a secured reachable Ollama-compatible open-model endpoint, or implement/configure a hosted open-model provider. Never expose an unauthenticated Ollama server to the internet.

The Blueprint requires owner-provided secrets and a model endpoint. Applying it creates billable resources and is a separate deployment step. No resources have been created. Official documentation: [workers](https://render.com/docs/background-workers), [free limits](https://render.com/docs/free), [disks](https://render.com/docs/disks).

## Budgets and tracing

Declared budgets are in `agent/config.yaml`; measured p50/p95, tokens and paid API charges are in results JSON. Full-graph latency includes MCP and model calls; retrieval-only timings do not measure the product. Cold startup and concurrent GPU experiments can dominate latency. Paid API spend is zero for local runs, not zero total operating cost. Hardware/electricity/hosting costs are unmeasured.

Phoenix receives OTLP spans when configured. Tool arguments/results and node usage are masked in the append-only audit, and every call carries a run trace ID. OAuth tokens are encrypted and never included in trace records. Pattern PII masking is imperfect; review exports before publishing public traces.
