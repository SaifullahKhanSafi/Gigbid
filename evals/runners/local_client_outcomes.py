"""Measures our own synthetic client outcomes, never official GigSim success."""

import argparse
import asyncio
import numpy as np
from rag.retriever import retrieve
from agent.nodes.logic import extractive_draft, quote
from support.simulated_clients import judge_proposal
from evals.runners.common import dataset, save


async def run(limit=30):
    jobs = [x for x in dataset() if x["bid"]]
    balanced = [
        next(x for x in jobs if x["persona"] == p and x["job"]["id"].endswith(f"{i:04d}"))
        for i in range(1, 11)
        for p in ["ml", "web", "data"]
        if any(x["persona"] == p and x["job"]["id"].endswith(f"{i:04d}") for x in jobs)
    ][:limit]
    rows = []
    for item in balanced:
        job = item["job"]
        evidence = retrieve(job["description"], item["persona"], 5, requirements=job["skills"])
        price = quote(job, 20, 45).amount
        drafts = {
            "generic": "Hello, I can do this job. I would discuss the requirements and start immediately.",
            "evidence_grounded": extractive_draft(
                job, evidence, "I would agree acceptance tests on a sample input before implementing the full scope."
            ),
        }
        for strategy, text in drafts.items():
            try:
                outcome = await judge_proposal(job, text, price, evidence)
                rows.append(
                    {
                        "job_id": job["id"],
                        "persona": item["persona"],
                        "strategy": strategy,
                        "proposal": text,
                        "price": price,
                        **outcome,
                    }
                )
            except Exception as e:
                rows.append(
                    {
                        "job_id": job["id"],
                        "persona": item["persona"],
                        "strategy": strategy,
                        "error": str(e),
                        "stage": "error",
                    }
                )
        print("local client", len(rows) // 2, flush=True)
        save("local_client_outcomes", {"status": "running", "rows": rows, "official_gigsim": False})
    summary = {}
    for strategy in ["generic", "evidence_grounded"]:
        rs = [r for r in rows if r["strategy"] == strategy]
        summary[strategy] = {
            "n": len(rs),
            "reply_or_later_rate": sum(r["stage"] in ("replied", "interview", "hired") for r in rs) / len(rs),
            "hire_rate": sum(r["stage"] == "hired" for r in rs) / len(rs),
            "error_rate": sum(r["stage"] == "error" for r in rs) / len(rs),
            "p95_client_seconds": float(np.percentile([r["seconds"] for r in rs if "seconds" in r], 95)),
        }
    return save(
        "local_client_outcomes",
        {
            "status": "complete",
            "official_gigsim": False,
            "simulator": "GigBid independent LLM clients v1",
            "summary": summary,
            "rows": rows,
            "limitations": [
                "Synthetic independently seeded client preferences and open-model judgments; not observed human behavior",
                "Client model is not human-calibrated",
                "Only synthetic bid-eligible jobs; price is held equal between strategies",
                "The same model family may favor its own phrasing",
                "No actual proposals/messages sent during this experiment",
            ],
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=30)
    asyncio.run(run(parser.parse_args().limit))
