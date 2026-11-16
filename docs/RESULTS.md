# Executed results

These are local development measurements on explicitly synthetic labels unless the source is marked real. They are not official GigSim or hidden-test results. Paid API costs exclude hardware/electricity/hosting.

## Retrieval

Source: [retrieval.json](../evals/results/retrieval.json). Project-level gold; empty gold excluded from recall. Timings are retrieval only and include cached queries after initial calls.

| Variant | Recall@5 | MRR | nDCG@10 | p95 seconds |
|---|---:|---:|---:|---:|
| V0 | 0.9595 | 1.0000 | 0.9714 | 0.0156 |
| V1 | 0.9794 | 1.0000 | 0.9913 | 0.0052 |
| V2 | 0.9794 | 1.0000 | 0.9863 | 0.0041 |
| V3 | 0.9653 | 1.0000 | 0.9759 | 0.0379 |
| V4 | 0.9794 | 1.0000 | 0.9863 | 0.0050 |
| V8 | 0.9653 | 1.0000 | 0.9759 | 0.0490 |

Selected: **V1**, provisionally. Synthetic template overlap inflates these scores. Cross-encoder reranking did not beat decomposition. Official reply rate and calibrated judge score: unavailable.

## Tool design

Source: [tools.json](../evals/results/tools.json). Forty synthetic tasks per design; JSON selection rather than native call execution.

| Design | Selection accuracy | Argument accuracy | Mean tokens |
|---|---:|---:|---:|
| fine | 0.875 | 0.875 | 288.5 |
| coarse | 0.700 | 0.450 | 253.7 |
| rewritten | 1.000 | 0.925 | 452.6 |

## Architecture comparison

Source: [architectures.json](../evals/results/architectures.json). Same fifty jobs, uniform 1.5B model. Errors count as incorrect. Handwritten rules overlap synthetic gold; decision correctness does not imply an approved draft.

| Architecture | Bid accuracy | Execution failure | Unsupported / completed job | p95 s | Tokens |
|---|---:|---:|---:|---:|---:|
| single_react | 0.580 | 0.060 | 2.021 | 4.32 | 81723 |
| prebuilt_supervisor | 0.300 | 0.260 | 0.459 | 7.70 | 134341 |
| handwritten | 1.000 | 0.000 | 0.000 | 14.26 | 315971 |

Handwritten graph terminal states on the uniform small-model run: `{'skipped': 9, 'needs_attention': 41}`. Needs-attention drafts were not sent. Supervisor schema integration failures were fixed and the same fifty jobs rerun; original records are retained. These systems differ in deterministic safeguards, so this is a product-system comparison rather than proof of a general multi-agent reasoning advantage.

## Local models

Source: [models.json](../evals/results/models.json). Thirty writer tasks per profile after explicit schemas. Unverified raw-plan sentences are conservatively rejected; that metric is not calibrated factual hallucination accuracy.

| Profile | Valid JSON | Rejected raw sentences / plan | Final unsupported | p95 s | Generation tokens/s |
|---|---:|---:|---:|---:|---:|
| open_small | 1.000 | 0.900 | 0.000 | 0.88 | 220.0 |
| open | 1.000 | 0.900 | 0.000 | 1.36 | 74.9 |

The schema fix improved the smallest model from the failed initial run in `models_before_schema_fix.json`. Both final writer configurations had valid structured output, but persuasive quality has not been independently rated. The 7B writer remains provisional; no human-quality superiority is claimed.

## Decisions, data, safety and extension

- [decisions.json](../evals/results/decisions.json): 600 jobs; bid/skip F1 1.000; scam precision/recall 1.000/1.000; proposed price inside synthetic band 0.945. The price metric includes skipped low-budget jobs; rule-derived labels share definitions with guards.
- [real_data.json](../evals/results/real_data.json): real Kaggle snapshot, 53,058 input and 52,976 retained rows; 81 duplicate and 1 invalid rows removed; 466 records changed by PII masking. Source/license and chronological split are documented in DATA_CARD.
- [agency.json](../evals/results/agency.json): mean supported requirement coverage 0.900 with routing, 0.467 for ML-only assignment. Shared synthetic skill ontology limits generalization.
- [safety.json](../evals/results/safety.json): detector flagged 70.0% of a small attack suite. This is detector recall, not model jailbreak ASR. Deliberately fabricated claim probes went from 2 verifier-rejected claims to 0 remaining after removal.

## Unavailable measurements

Official GigSim replies/hires, hidden results, independently human-calibrated judge scores, blind-panel preferences, actual November 2 policy adaptation and public deployment uptime are unavailable. Values remain null. No synthetic proxy is labelled as an official outcome.
