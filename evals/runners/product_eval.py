"""Production open-profile graph readiness/latency; stops at real approval interrupts."""

import argparse
import asyncio
import json
import os
import time
import uuid
from collections import Counter
import numpy as np
from langgraph.checkpoint.memory import InMemorySaver
from core import db
from core.settings import ROOT
from agent.mcp_client import ToolGateway
from agent.graphs.bid_graph import build_bid_graph
from evals.runners.common import dataset, save


async def run(limit=30):
    os.environ["GIGBID_MODEL_PROFILE"] = "open"
    os.environ["GIGBID_MCP_TRANSPORT"] = "http"
    for i, name in enumerate(["portfolio", "marketplace", "workspace"]):
        os.environ.setdefault(name.upper() + "_MCP_URL", f"http://127.0.0.1:{8101 + i}/mcp")
    market = json.loads((ROOT / "data/processed/market_stats.json").read_text())["categories"]
    rows = []
    for item in dataset(limit):
        job = item["job"]
        user = "product-eval-" + uuid.uuid4().hex
        trace = uuid.uuid4().hex
        profile = {
            "persona": item["persona"],
            "floor_rate": 20,
            "weekly_connects": 100,
            "market_median": market[item["persona"]]["hourly_usd_median"],
        }
        db.put(user, "settings", "profile", profile)
        db.put(user, "job", job["id"], job)
        start = time.perf_counter()
        try:
            async with ToolGateway(user, trace) as gateway:
                graph = build_bid_graph(gateway, InMemorySaver(), profile)
                result = await graph.ainvoke(
                    {
                        "tenant": user,
                        "trace_id": trace,
                        "job_id": job["id"],
                        "persona": item["persona"],
                        "events": [],
                        "steps": 0,
                        "tokens": 0,
                    },
                    {"configurable": {"thread_id": trace}, "recursion_limit": 40},
                )
                rows.append(
                    {
                        "job_id": job["id"],
                        "persona": item["persona"],
                        "status": result.get("status"),
                        "correct_decision": (result.get("decision", {}).get("action") == "bid") == item["bid"],
                        "gold_bid": item["bid"],
                        "seconds": time.perf_counter() - start,
                        "tokens": result.get("tokens", 0),
                        "revision": result.get("revision", 0),
                        "critique": result.get("critique"),
                        "error": result.get("error"),
                        "proposal": result.get("draft", {}).get("text"),
                        "events": result.get("events", []),
                    }
                )
        except Exception as e:
            rows.append(
                {
                    "job_id": job["id"],
                    "persona": item["persona"],
                    "status": "error",
                    "correct_decision": False,
                    "gold_bid": item["bid"],
                    "seconds": time.perf_counter() - start,
                    "error": str(e),
                }
            )
        save("product_open_profile", {"status": "running", "rows": rows})
        print("product open", len(rows), rows[-1]["status"], flush=True)
    eligible = [r for r in rows if r["gold_bid"]]
    summary = {
        "n": len(rows),
        "terminal_states": dict(Counter(r["status"] for r in rows)),
        "bid_accuracy": sum(r["correct_decision"] for r in rows) / len(rows),
        "eligible_draft_ready_rate": sum(r["status"] == "awaiting_approval" for r in eligible) / len(eligible),
        "p50_job_seconds": float(np.percentile([r["seconds"] for r in rows], 50)),
        "p95_job_seconds": float(np.percentile([r["seconds"] for r in rows], 95)),
        "p95_eligible_proposal_seconds": float(np.percentile([r["seconds"] for r in eligible], 95)),
        "total_tokens": sum(r.get("tokens", 0) for r in rows),
        "paid_api_usd": 0,
    }
    return save(
        "product_open_profile",
        {
            "status": "complete",
            "profile": "open: 1.5B analyst, 7B writer/critic",
            "summary": summary,
            "rows": rows,
            "limitations": [
                "Small synthetic dev set with shared ontology",
                "No mutation is approved or sent by this evaluation",
                "Not hidden-test or public-host latency",
                "Open profile readiness is separate from uniform-model architecture comparison",
            ],
        },
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=30)
    asyncio.run(run(p.parse_args().limit))
