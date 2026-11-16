import argparse
import time
import numpy as np
from sklearn.metrics import f1_score, precision_score, recall_score, accuracy_score
from rag.retriever import retrieve
from agent.nodes.logic import fit_report, assess_risk, decide, quote
from evals.runners.common import dataset, save


def run(limit=None, output_name="decisions"):
    rows = []
    for item in dataset(limit):
        j = item["job"]
        start = time.perf_counter()
        evidence = retrieve(j["description"], item["persona"], 5, requirements=j["skills"])
        fit = fit_report(j["skills"], evidence)
        risk = assess_risk(j["description"], j["client"])
        decision = decide(fit.model_dump(), risk.model_dump(), j["budget_max"], 20)
        price = quote(j, 20, 45)
        rows.append(
            {
                "id": j["id"],
                "persona": item["persona"],
                "pred_bid": decision.action == "bid",
                "gold_bid": item["bid"],
                "pred_scam": risk.scam,
                "gold_scam": item["scam"],
                "price": price.amount,
                "in_fair_band": item["fair_price_band"][0] <= price.amount <= item["fair_price_band"][1],
                "seconds": time.perf_counter() - start,
                "decision_reasons": decision.reasons,
            }
        )
    summary = {}
    for p in ["all", "ml", "web", "data"]:
        rs = [r for r in rows if p == "all" or r["persona"] == p]
        summary[p] = {
            "jobs": len(rs),
            "bid_f1": f1_score([r["gold_bid"] for r in rs], [r["pred_bid"] for r in rs], zero_division=0),
            "bid_accuracy": accuracy_score([r["gold_bid"] for r in rs], [r["pred_bid"] for r in rs]),
            "scam_precision": precision_score(
                [r["gold_scam"] for r in rs], [r["pred_scam"] for r in rs], zero_division=0
            ),
            "scam_recall": recall_score([r["gold_scam"] for r in rs], [r["pred_scam"] for r in rs], zero_division=0),
            "price_in_band": float(np.mean([r["in_fair_band"] for r in rs])),
            "p95_seconds": float(np.percentile([r["seconds"] for r in rs], 95)),
        }
    failures = [r for r in rows if r["gold_bid"] != r["pred_bid"] or not r["in_fair_band"]]
    return save(
        output_name,
        {
            "summary": summary,
            "rows": rows,
            "failures": failures,
            "limitations": [
                "Rule-derived synthetic labels share definitions with guardrails",
                "This evaluates pure decisions, not complete model graph latency",
            ],
        },
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int)
    run(p.parse_args().limit)
