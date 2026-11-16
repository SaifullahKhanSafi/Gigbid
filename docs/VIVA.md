# Viva guide

1. **Kill Marketplace MCP.** Stop only the launcher-owned marketplace PID. Health reports unavailable; runs queue/retry. Restart through the launcher. Inspect `agent/mcp_client.py`, worker retry state and the degraded banner.
2. **Crash after approval.** Check `tests/integration/test_graph.py`: a new graph/checkpointer resumes the same thread; the receipt key binds exact payload and wallet transaction. The local test also replays dispatch and proves balance unchanged.
3. **Delete evidence.** Settings/API tombstones an item and increments the index revision. Dispatch re-reads cited evidence through MCP; a missing item blocks/error-stops the send. Explain why an earlier approval is insufficient.
4. **Wrong skip.** Open `/runs`, then the job's risk/fit/decision events. Compare the specific dev label and source result row, not a generic explanation.
5. **Injection.** Run the safety suite. Some indirect attacks miss the pattern detector. They still lack an exact-content human grant; explain that detector recall and authorization are different guarantees.
6. **Memory.** Three distinct repeated deletions promote style; five outcome observations plus a configured positive-rate threshold promote outcome memory. Delete promoted items in Settings. Local reply observations are synthetic fixtures.
7. **Live mode.** Explain port/config switch, encrypted OAuth storage and explicit discovered tool mapping. Real Upwork connection and tool semantics remain unverified; do not claim a demo you have not run.
8. **Judge disagreement.** No human-calibrated judge is reported yet. Complete `evals/datasets/human_calibration.csv` honestly and run the calibration script before discussing kappa.
9. **Single vs graph.** Read the measured table and failed traces. The graph's rule-derived synthetic decision advantage is not evidence that multi-agent reasoning generally wins.
10. **Policy update.** Official November 2 change was absent. The local policy-change rehearsal modifies only configuration, with a test/diff. Identify it as a rehearsal, not the official update.

Be ready to trace one actual proposal sentence to its cited item, explain reducers and Send/join, show the interrupt checkpoint, describe an idempotency collision, and distinguish posted budget statistics from successful earnings.
