# Preregistered local development experiments

Written before the first retrieval/model comparison in this project.

- H-A: more precise tool descriptions improve argument accuracy on 40 synthetic known-call tasks; compare fine, coarse, and rewritten descriptions using the same open model and deterministic decoding. Count model errors as failures.
- H-B: requirement decomposition with BM25/dense RRF improves project evidence Recall@5 over whole-job dense retrieval. Evaluate V0,V1,V2,V3,V4,V8 on the same synthetic development split. Select by nDCG@10, break ties with Recall@5 then latency. Run component ablations and persona/job-type breakdowns. Template overlap may inflate every variant's scores.
- H-C: a hand-built graph has fewer unsafe proposed actions than single ReAct and a prebuilt supervisor on 50 fixed jobs, at higher token/latency cost. Only actual model executions can answer this; deterministic graph/rule tests are separate evidence.
- H-M: Qwen 2.5 7B writer/critic outperforms a 0.5B-only configuration on plan relevance/grounding, with greater latency. Compare raw structured validity, conservative verification and measured tokens/second; human and calibrated-judge quality remain unmeasured until labels exist.
- H-X1: agency routing increases supported requirement coverage compared with assigning every job to the ML persona. Do not read persona_hint or gold labels during routing.

Missing official GigSim, independent human relevance labels, human calibration labels and blind-panel ratings limit external validity. Report these as missing rather than claiming completion from synthetic proxies.
