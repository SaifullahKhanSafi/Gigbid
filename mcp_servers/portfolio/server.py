from mcp_servers.contracts import EvidenceOutput, EvidenceSearchOutput, SkillsOutput, TeamRankOutput
from typing import Annotated
from pydantic import Field
from core.security import tenant
from core import db
from rag.retriever import retrieve
from rag.index.engine import load_corpus
from mcp_servers.common import server, http_app, READ, audit_call

mcp = server("GigBid Portfolio", 8101)


def corpus():
    user = tenant()
    profile = db.get(user, "settings", "profile") or {"persona": "ml"}
    deleted = {x["id"] for x in db.scan(user, "deleted_evidence")}
    return [
        x
        for x in load_corpus() + db.scan(user, "evidence")
        if (profile.get("agency_mode") or x["persona"] == profile.get("persona", "ml")) and x["id"] not in deleted
    ]


@mcp.tool(annotations=READ, structured_output=True)
def search_evidence(
    requirement: Annotated[str, Field(min_length=1, max_length=12000)],
    k: Annotated[int, Field(ge=1, le=20)] = 5,
    filters: dict | None = None,
    variant: str | None = None,
    requirements: list[str] | None = None,
    trace_id: str = "local",
) -> EvidenceSearchOutput:
    """Find delivered project evidence for requirements in the active persona. Returns source/date/type/outcome and approved facts; no invented credentials."""
    profile = db.get(tenant(), "settings", "profile") or {"persona": "ml"}
    persona = profile.get("persona", "ml")
    filters = dict(filters or {})
    if filters.get("persona", persona) != persona:
        raise PermissionError("Change your active persona before searching another corpus")
    result = {"items": retrieve(requirement, persona, k, variant, requirements, tenant(), filters)}
    audit_call("search_evidence", {"requirement": requirement, "k": k}, result, trace_id)
    return result


@mcp.tool(annotations=READ, structured_output=True)
def rank_team(requirement: str, requirements: list[str], trace_id: str = "local") -> TeamRankOutput:
    """Agency mode only: rank this tenant's three fictional members by requirement evidence coverage. Never uses a job's expected persona or evaluation labels."""
    profile = db.get(tenant(), "settings", "profile") or {}
    if not profile.get("agency_mode"):
        raise PermissionError("Enable agency mode to compare team members")
    from agent.nodes.logic import fit_report

    reports = {}
    for persona in ("ml", "web", "data"):
        items = retrieve(requirement, persona, 5, requirements=requirements, tenant=tenant())
        report = fit_report(requirements, items)
        report.persona = persona
        reports[persona] = report.model_dump()
    selected = max(reports, key=lambda p: reports[p]["score"])
    result = {
        "selected_persona": selected,
        "fit": reports[selected],
        "member_scores": {p: r["score"] for p, r in reports.items()},
    }
    audit_call("rank_team", {"requirements": requirements}, result, trace_id)
    return result


@mcp.tool(annotations=READ, structured_output=True)
def get_case_study(id: str, trace_id: str = "local") -> EvidenceOutput:
    """Get one full evidence item from the authenticated active persona corpus."""
    item = next((x for x in corpus() if x["id"] == id), None)
    if item is None:
        raise ValueError("Evidence not found in your corpus")
    audit_call("get_case_study", {"id": id}, item, trace_id)
    return item


@mcp.tool(annotations=READ, structured_output=True)
def list_skills(trace_id: str = "local") -> SkillsOutput:
    """List observed portfolio skills with evidence counts, never self-asserted proficiency."""
    from collections import Counter

    result = {"skills": dict(Counter(s for x in corpus() for s in x["skills"]))}
    audit_call("list_skills", {}, result, trace_id)
    return result


@mcp.resource("portfolio://case/{id}")
def case_resource(id: str) -> str:
    import json

    return json.dumps(get_case_study(id))


@mcp.resource("portfolio://proposal/{id}")
def proposal_resource(id: str) -> str:
    import json

    item = get_case_study(id)
    if item["type"] != "proposal":
        raise ValueError("Not a proposal")
    return json.dumps(item)


@mcp.prompt()
def answer_screening_question(question: str) -> str:
    """Ground a screening answer in specific case studies and disclose missing experience."""
    from core.settings import ROOT
    return (ROOT/'agent/prompts/screening.v1.md').read_text().format(question=repr(question))


app = http_app(mcp)
if __name__ == "__main__":
    import os

    if os.getenv("MCP_HTTP") == "1":
        import uvicorn

        uvicorn.run(
            app,
            host="127.0.0.1" if os.getenv("GIGBID_ENV") != "production" else "0.0.0.0",
            port=int(os.getenv("MCP_PORT", "8101")),
            access_log=False,
        )
    else:
        mcp.run()
