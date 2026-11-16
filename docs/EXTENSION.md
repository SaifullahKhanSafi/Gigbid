# X1: Agency routing

The extension scores every job against each of the ML, web and data persona corpora, then chooses the member with the greatest supported-requirement coverage. It uses the same retriever and fit-scoring function as the bid graph. Ties are deterministic. It does not use `persona_hint`, dev gold labels or a job's expected persona to choose a member.

Run `python -m evals.runners.agency_eval`. Results and per-job coverage are in `evals/results/agency.json`, comparing agency routing with always assigning the ML member. The synthetic shared-skill ontology makes this an optimistic routing check. Unknown/unsupported jobs still require a skip decision; routing to the least-bad member is not evidence of suitability.

Enable Agency mode in Settings to show the combined feed. Fit calls the read-only Portfolio MCP rank_team tool, chooses a member, and retains that persona in the graph state. The studio names the routed member. Send-time evidence reads are allowed across this tenant's team only while agency mode remains enabled; other tenants stay isolated. The agency test checks the permission gate, web-skill routing and evidence revalidation.
