# Final validation — November 16, 2026

Executed against the final local source:

| Check | Result |
|---|---|
| Python unit, integration and contract suite | 28 passed; two dependency deprecation warnings |
| Playwright with system Chrome | 6 passed; deterministic model doubles |
| TypeScript and Vite production build | Passed |
| Ruff source checks | Passed |
| uv dependency lock consistency | Passed; 164 resolved packages |
| Root Docker Compose configuration | Passed syntax validation; Docker daemon unavailable |
| Container image tag existence | Verified separately; not a container startup test |

Machine-readable evidence: `evals/results/python-tests.xml`, `delivery.json`, `container_tags.json`. The local browser HTML report remains under ignored `apps/web/playwright-report/`.

The final open-model product check reached approval on all 27 eligible jobs among 30 fixed synthetic development jobs (three skipped). No sends occurred in that check. Its routed model profile differs from the uniform-model orchestration experiment.

The additional local client experiment compared 30 generic with 30 evidence-grounded proposals at identical job prices. Reply-or-later rates were 46.7% and 76.7%; hire rates were 43.3% and 40.0%. Generic evaluation errors were 6.7%, grounded errors 0%. The evidence does not establish improved hiring. The synthetic model judge is not human calibrated and sometimes attributes supplied portfolio experience to a generic proposal. This is an exploratory local simulator result, not official GigSim or real Upwork performance.

Own-portfolio mode excludes the fictional corpus and disables the fictional agency. Dispatch tests cover evidence removal, replay after a crash following marketplace commit, and atomic/idempotent spending. Live feed and draft-only Upwork behavior have mock contract coverage, not real account verification.

The MP4 documents an earlier local build using real proposal models and explicitly labelled fixture client replies. Current production local mode uses queued LLM clients. Neither constitutes official GigSim evaluation.

Remaining externally dependent requirements are listed in [STATUS](STATUS.md). Official test assets, human ratings and account/service publication must not be fabricated.
