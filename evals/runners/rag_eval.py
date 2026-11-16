import argparse
import time
import numpy as np
from rag.retriever import retrieve, VARIANTS
from evals.runners.common import dataset, metrics, mean, save
from agent.nodes.logic import extractive_draft
from rag.verify import verify


def run(limit=None, variants=None):
    rows = []
    for variant in variants or VARIANTS:
        for n, item in enumerate(dataset(limit)):
            job = item["job"]
            start = time.perf_counter()
            evidence = retrieve(job["description"], item["persona"], 10, variant, job["skills"])
            elapsed = time.perf_counter() - start
            # Gold is project-level: collapse equivalent README/code/case renderings.
            gold = {x.rsplit("-", 1)[0] for x in item["gold_evidence"]}
            retrieved = []
            for e in evidence:
                if e["project"] not in retrieved:
                    retrieved.append(e["project"])
            m = metrics(retrieved, gold)
            text = extractive_draft(job, evidence)
            checked = verify(text, evidence)
            before = sum(c.status in ("unsupported", "partly_supported") for c in checked.claims)
            after = verify(checked.text, evidence)
            rows.append(
                {
                    "variant": variant,
                    "job_id": job["id"],
                    "persona": item["persona"],
                    "job_type": item["job_type"],
                    "seconds": elapsed,
                    "retrieved": retrieved,
                    "gold": sorted(gold),
                    **(m or {"recall_at_5": None, "mrr": None, "ndcg_at_10": None}),
                    "unsupported_before": before,
                    "unsupported_after": sum(c.status in ("unsupported", "partly_supported") for c in after.claims),
                }
            )
            if n % 60 == 0:
                print(variant, n, flush=True)
    summary = {}
    for variant in variants or VARIANTS:
        group = [r for r in rows if r["variant"] == variant]
        summary[variant] = {
            **{
                k: mean(group, k)
                for k in ["recall_at_5", "mrr", "ndcg_at_10", "unsupported_before", "unsupported_after"]
            },
            "p50_seconds": float(np.percentile([r["seconds"] for r in group], 50)),
            "p95_seconds": float(np.percentile([r["seconds"] for r in group], 95)),
            "jobs": len(group),
            "official_reply_rate": None,
            "judge_score": None,
            "api_usd": 0,
            "by_persona": {
                p: {k: mean([r for r in group if r["persona"] == p], k) for k in ["recall_at_5", "mrr", "ndcg_at_10"]}
                for p in ["ml", "web", "data"]
            },
            "by_job_type": {
                p: {k: mean([r for r in group if r["job_type"] == p], k) for k in ["recall_at_5", "mrr", "ndcg_at_10"]}
                for p in ["standard", "multi_requirement", "unsupported"]
            },
        }
    chosen = max(
        summary,
        key=lambda v: (summary[v]["ndcg_at_10"] or 0, summary[v]["recall_at_5"] or 0, -summary[v]["p95_seconds"]),
    )
    return save(
        "retrieval",
        {
            "summary": summary,
            "selected_variant": chosen,
            "selection_rule": "nDCG@10, Recall@5, then p95 latency; synthetic local dev only",
            "rows": rows,
            "limitations": [
                "Shared synthetic ontology and templates",
                "Gold project relevance, not independent sentence relevance",
                "Empty gold cases excluded from recall averages and evaluated by decisions",
                "Latency includes cold model/index loading for first item; later queries are cached",
                "Extractive proposals are used here; this is not an LLM writer-quality evaluation",
            ],
        },
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int)
    p.add_argument("--variants", nargs="+", choices=list(VARIANTS))
    a = p.parse_args()
    run(a.limit, a.variants)
