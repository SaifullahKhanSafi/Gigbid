"""Actual ReAct, langgraph-supervisor and handwritten graph on the same fixed jobs.

Uniform 1.5B model isolates orchestration from the deployed 7B writer routing.
No proposals leave the local simulator; graph executions stop at interrupts.
"""

import argparse
import asyncio
import json
import os
import time
import uuid
from typing import Literal
import numpy as np
from pydantic import BaseModel
from langchain_core.tools import tool
from langchain_core.callbacks import BaseCallbackHandler
from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent
from langgraph_supervisor import create_supervisor
from langgraph.prebuilt.chat_agent_executor import AgentStateWithStructuredResponse
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from core import db
from core.settings import ROOT
from agent.mcp_client import ToolGateway
from agent.graphs.bid_graph import build_bid_graph
from rag.verify import verify
from agent.nodes.logic import compliance
from evals.runners.common import dataset, save


class Answer(BaseModel):
    decision: Literal["bid", "skip"]
    text: str
    reasons: list[str]


class Usage(BaseCallbackHandler):
    def __init__(self):
        self.input = 0
        self.output = 0

    def on_llm_end(self, response, **kwargs):
        for group in response.generations:
            for generation in group:
                usage = getattr(generation.message, "usage_metadata", None) or {}
                self.input += usage.get("input_tokens", 0)
                self.output += usage.get("output_tokens", 0)


async def run(limit=50, architectures=None):
    output_name = os.getenv("GIGBID_EVAL_OUTPUT", "architectures")
    os.environ["GIGBID_MODEL_PROFILE"] = "comparison"
    os.environ["GIGBID_MCP_TRANSPORT"] = "http"
    for i, name in enumerate(["portfolio", "marketplace", "workspace"]):
        os.environ.setdefault(name.upper() + "_MCP_URL", f"http://127.0.0.1:{8101 + i}/mcp")
    model = ChatOllama(
        model="qwen2.5:1.5b",
        base_url=os.getenv("OLLAMA_URL", "http://127.0.0.1:11434"),
        temperature=0,
        num_predict=300,
        num_ctx=4096,
        seed=4016,
    )
    prompt = lambda name: (ROOT / f"agent/prompts/{name}.v1.md").read_text()
    rows = []
    for architecture in architectures or ["single_react", "prebuilt_supervisor", "handwritten"]:
        for n, item in enumerate(dataset(limit)):
            job = item["job"]
            user = "arch-" + uuid.uuid4().hex
            trace = uuid.uuid4().hex
            db.put(user, "settings", "profile", {"persona": item["persona"], "floor_rate": 20, "weekly_connects": 100})
            db.put(user, "job", job["id"], job)
            evidence = []
            usage = Usage()
            start = time.perf_counter()
            try:
                async with ToolGateway(user, trace) as gateway:

                    @tool
                    async def portfolio_evidence(requirement: str, skills: list[str]) -> dict:
                        """Retrieve up to five portfolio evidence items for requirements and exact skills."""
                        result = await gateway.call(
                            "fit", "search_evidence", requirement=requirement, requirements=skills, k=5
                        )
                        evidence.extend(result["items"])
                        return result

                    @tool
                    async def client_history(client_id: str) -> dict:
                        """Read the client's verified payment, rating, hires and spend for risk assessment."""
                        return await gateway.call("risk", "get_client_history", client_id=client_id)

                    @tool
                    async def connects_balance() -> dict:
                        """Read remaining Connects. Does not spend any."""
                        return await gateway.call("pricing", "get_connects_balance")

                    @tool
                    async def preview_proposal(text: str, amount: float) -> dict:
                        """Dry-run proposal payload and cost. Never submits or spends."""
                        return await gateway.call(
                            "approval",
                            "submit_proposal",
                            request={
                                "idempotency_key": "eval-" + trace,
                                "job_id": job["id"],
                                "text": text,
                                "amount": amount,
                                "dry_run": True,
                            },
                        )

                    tools = [portfolio_evidence, client_history, connects_balance, preview_proposal]
                    if architecture == "handwritten":
                        async with AsyncSqliteSaver.from_conn_string(":memory:") as saver:
                            graph = build_bid_graph(gateway, saver, {"persona": item["persona"], "floor_rate": 20})
                            result = await asyncio.wait_for(
                                graph.ainvoke(
                                    {
                                        "tenant": user,
                                        "job_id": job["id"],
                                        "trace_id": trace,
                                        "persona": item["persona"],
                                        "steps": 0,
                                        "tokens": 0,
                                        "events": [],
                                    },
                                    {"configurable": {"thread_id": trace}, "recursion_limit": 40},
                                ),
                                timeout=120,
                            )
                            decision = result.get("decision", {}).get("action", "skip")
                            text = result.get("draft", {}).get("text", "")
                            evidence = result.get("fit", {}).get("evidence", [])
                            input_tokens = sum(
                                e.get("usage", {}).get("prompt_tokens", 0) for e in result.get("events", [])
                            )
                            output_tokens = sum(
                                e.get("usage", {}).get("completion_tokens", 0) for e in result.get("events", [])
                            )
                            status = result.get("status")
                            caught = len(result.get("compliance", {}).get("violations", []))
                    else:
                        if architecture == "single_react":
                            graph = create_react_agent(
                                model, tools, prompt=prompt("baseline_single"), response_format=Answer, name="single"
                            )
                        else:
                            research = create_react_agent(
                                model, tools[:3], prompt=prompt("baseline_research"), name="research"
                            )
                            writer = create_react_agent(
                                model, [preview_proposal], prompt=prompt("baseline_writer"), name="proposal"
                            )
                            graph = create_supervisor(
                                [research, writer],
                                model=model,
                                prompt=prompt("baseline_supervisor"),
                                response_format=Answer,
                                output_mode="full_history",
                                state_schema=AgentStateWithStructuredResponse,
                            ).compile()
                        result = await asyncio.wait_for(
                            graph.ainvoke(
                                {"messages": [("user", json.dumps({"job": job, "hourly_floor": 20}))]},
                                {"recursion_limit": 14, "callbacks": [usage]},
                            ),
                            timeout=120,
                        )
                        answer = result.get("structured_response")
                        answer = answer.model_dump() if hasattr(answer, "model_dump") else answer
                        if not isinstance(answer, dict):
                            raise ValueError("Agent did not return structured decision")
                        decision = answer["decision"]
                        text = answer["text"]
                        input_tokens = usage.input
                        output_tokens = usage.output
                        status = "evaluated"
                        caught = len(compliance(text, evidence).violations)
                    checked = verify(text, evidence)
                    rows.append(
                        {
                            "architecture": architecture,
                            "job_id": job["id"],
                            "persona": item["persona"],
                            "gold_bid": item["bid"],
                            "pred_bid": decision == "bid",
                            "correct": (decision == "bid") == item["bid"],
                            "unsupported_claims": sum(
                                c.status in ("unsupported", "partly_supported") for c in checked.claims
                            )
                            if decision == "bid"
                            else 0,
                            "compliance_violations_detected": caught,
                            "seconds": time.perf_counter() - start,
                            "input_tokens": input_tokens,
                            "output_tokens": output_tokens,
                            "status": status,
                            "text": text,
                            "official_reply_rate": None,
                        }
                    )
            except Exception as e:
                import traceback

                rows.append(
                    {
                        "architecture": architecture,
                        "job_id": job["id"],
                        "persona": item["persona"],
                        "gold_bid": item["bid"],
                        "correct": False,
                        "error": str(e),
                        "error_detail": traceback.format_exc(),
                        "seconds": time.perf_counter() - start,
                        "input_tokens": usage.input,
                        "output_tokens": usage.output,
                        "official_reply_rate": None,
                    }
                )
            if n % 5 == 0:
                print(architecture, n, flush=True)
            save(output_name, {"status": "running", "rows": rows})
    summary = {}
    for a in architectures or ["single_react", "prebuilt_supervisor", "handwritten"]:
        rs = [r for r in rows if r["architecture"] == a]
        summary[a] = {
            "n": len(rs),
            "bid_accuracy": sum(r["correct"] for r in rs) / len(rs),
            "execution_failure_rate": sum("error" in r for r in rs) / len(rs),
            "unsupported_claims_per_completed_job": float(
                np.mean([r["unsupported_claims"] for r in rs if "unsupported_claims" in r])
            )
            if any("unsupported_claims" in r for r in rs)
            else None,
            "p95_seconds": float(np.percentile([r["seconds"] for r in rs], 95)),
            "total_tokens": sum(r.get("input_tokens", 0) + r.get("output_tokens", 0) for r in rs),
            "official_reply_rate": None,
        }
    return save(
        output_name,
        {
            "status": "complete",
            "summary": summary,
            "rows": rows,
            "model": "qwen2.5:1.5b uniformly",
            "limitations": [
                "Synthetic labelled jobs; no official client outcomes",
                "Failures count as incorrect decisions",
                "Handwritten graph includes deterministic risk/fit rules; this is a product-system comparison, not pure model reasoning",
                "Local MCP tools are real; no outgoing proposal is approved in this experiment",
            ],
        },
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=50)
    p.add_argument("--only", nargs="+", choices=["single_react", "prebuilt_supervisor", "handwritten"])
    args = p.parse_args()
    asyncio.run(run(args.limit, args.only))
