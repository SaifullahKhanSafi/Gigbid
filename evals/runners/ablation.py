"""Reuses the full measured component variants; never relabels a missing experiment."""

import json
from core.settings import ROOT
from evals.runners.common import save


def run():
    data = json.loads((ROOT / "evals/results/retrieval.json").read_text())
    summary = data["summary"]
    pairs = [
        ("decomposition", "V0", "V1"),
        ("BM25 fusion", "V1", "V2"),
        ("cross encoder", "V2", "V3"),
        ("historical outcomes", "V2", "V4"),
        ("corrective abstention", "V3", "V8"),
    ]
    rows = [
        {
            "component": component,
            "without": a,
            "with": b,
            "delta_recall_at_5": summary[b]["recall_at_5"] - summary[a]["recall_at_5"],
            "delta_ndcg_at_10": summary[b]["ndcg_at_10"] - summary[a]["ndcg_at_10"],
        }
        for component, a, b in pairs
        if a in summary and b in summary
    ]
    return save(
        "ablation",
        {
            "rows": rows,
            "source": "retrieval.json",
            "note": "Paired component additions; V0→V1 also changes query aggregation. Not a full factorial ablation.",
        },
    )


if __name__ == "__main__":
    run()
