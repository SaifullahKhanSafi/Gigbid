import argparse
import asyncio
import os
import time
import numpy as np
from agent.model import generate
from agent.nodes.logic import extractive_draft
from rag.retriever import retrieve
from rag.verify import verify
from evals.runners.common import dataset, save


async def run(limit=30):
    rows = []
    for profile in ["open_small", "open"]:
        os.environ["GIGBID_MODEL_PROFILE"] = profile
        for n, item in enumerate(dataset(limit)):
            job = item["job"]
            evidence = retrieve(job["description"], item["persona"], 5, requirements=job["skills"])
            start = time.perf_counter()
            try:
                result = await generate("writer", {"job": job, "evidence": evidence}, "model-eval-" + job["id"])
                plan = result["output"].get("plan", "")
                valid = isinstance(plan, str) and bool(plan.strip())
                plan = plan if isinstance(plan, str) else ""
                raw = verify(plan, [])
                draft = extractive_draft(job, evidence, plan)
                checked = verify(draft, evidence)
                duration = result.get("eval_duration_ns", 0) / 1e9
                rows.append(
                    {
                        "profile": profile,
                        "job_id": job["id"],
                        "persona": item["persona"],
                        "valid_plan_json": valid,
                        "raw_plan": plan,
                        "raw_unsupported": sum(c.status in ("unsupported", "partly_supported") for c in raw.claims),
                        "final_unsupported": sum(
                            c.status in ("unsupported", "partly_supported")
                            for c in verify(checked.text, evidence).claims
                        ),
                        "seconds": time.perf_counter() - start,
                        "prompt_tokens": result["prompt_tokens"],
                        "completion_tokens": result["completion_tokens"],
                        "generation_tokens_per_second": result["completion_tokens"] / duration if duration else None,
                        "model": result["model"],
                        "usd": 0,
                    }
                )
            except Exception as e:
                rows.append(
                    {
                        "profile": profile,
                        "job_id": job["id"],
                        "valid_plan_json": False,
                        "error": str(e),
                        "seconds": time.perf_counter() - start,
                    }
                )
            if n % 5 == 0:
                print(profile, n, flush=True)
            save("models", {"rows": rows, "status": "running", "judge_calibrated": False})
    summary = {}
    for profile in ["open_small", "open"]:
        rs = [r for r in rows if r["profile"] == profile]
        summary[profile] = {
            "n": len(rs),
            "valid_plan_rate": sum(r["valid_plan_json"] for r in rs) / len(rs),
            "raw_unsupported_per_plan": float(np.mean([r.get("raw_unsupported", 0) for r in rs])),
            "final_unsupported_per_draft": float(np.mean([r.get("final_unsupported", 0) for r in rs])),
            "p50_seconds": float(np.percentile([r["seconds"] for r in rs], 50)),
            "p95_seconds": float(np.percentile([r["seconds"] for r in rs], 95)),
            "mean_generation_tokens_per_second": float(
                np.mean([r["generation_tokens_per_second"] for r in rs if r.get("generation_tokens_per_second")])
            ),
            "total_prompt_tokens": sum(r.get("prompt_tokens", 0) for r in rs),
            "total_completion_tokens": sum(r.get("completion_tokens", 0) for r in rs),
            "paid_api_usd": 0,
        }
    return save(
        "models",
        {
            "status": "complete",
            "summary": summary,
            "rows": rows,
            "judge_calibrated": False,
            "limitations": [
                "Automatic extractive safety metrics do not measure persuasive quality",
                "Human quality ratings and calibrated judge not available",
                "Local hardware/electricity costs are not zero; USD reports paid API charges only",
            ],
        },
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=30)
    asyncio.run(run(p.parse_args().limit))
