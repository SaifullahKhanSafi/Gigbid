from rag.retriever import retrieve
from agent.nodes.logic import fit_report
from evals.runners.common import dataset, save


def run(limit=60):
    rows = []
    for item in dataset(limit):
        j = item["job"]
        scores = {}
        for persona in ["ml", "web", "data"]:
            e = retrieve(j["description"], persona, 5, requirements=j["skills"])
            scores[persona] = fit_report(j["skills"], e).score
        chosen = max(scores, key=scores.get)
        rows.append(
            {
                "job_id": j["id"],
                "scores": scores,
                "chosen": chosen,
                "coverage": scores[chosen],
                "ml_only_coverage": scores["ml"],
                "gold_persona_for_evaluation_only": item["persona"],
            }
        )
    return save(
        "agency",
        {
            "extension": "X1 agency routing",
            "rows": rows,
            "mean_agency_coverage": sum(r["coverage"] for r in rows) / len(rows),
            "mean_ml_only_coverage": sum(r["ml_only_coverage"] for r in rows) / len(rows),
            "note": "Routes by evidence coverage. persona_hint and gold labels are not inputs to routing. Ties favor ML; unsupported jobs still need a skip decision.",
        },
    )


if __name__ == "__main__":
    run()
