import asyncio
import json
import time
import os
import numpy as np
import httpx
from core.settings import ROOT
from evals.runners.common import save

BASE = [
    ("get_job", {"job_id": "demo-ml-0001"}, "Read job demo-ml-0001."),
    ("get_client_history", {"client_id": "client-ml-1"}, "Read history of client client-ml-1."),
    ("get_connects_balance", {}, "Read my Connects balance."),
    ("search_jobs", {"query": "Python"}, "Search jobs for Python."),
    ("list_messages", {"conversation_id": "thread-12"}, "Read messages in conversation thread-12."),
    ("get_case_study", {"id": "ml-project-00-case_study"}, "Read case study ml-project-00-case_study."),
    ("list_skills", {}, "List the skills observed in my portfolio."),
    ("free_slots", {"days": 3}, "Find free calendar slots for the next 3 days."),
]


async def run():
    tasks = [
        {
            "id": i,
            "expected": name,
            "arguments": args,
            "task": text + (" Return only the requested result." if i // 8 % 2 else ""),
        }
        for i, (name, args, text) in enumerate(BASE * 5)
    ]
    fine = [{"name": name, "description": name.replace("_", " "), "arguments": list(args)} for name, args, _ in BASE]
    rewritten = [
        {
            "name": name,
            "description": text + " Read only; no sending, no spending. Exact required fields are listed.",
            "arguments": list(args),
        }
        for name, args, text in BASE
    ]
    coarse = [
        {
            "name": "marketplace_read",
            "description": "Read marketplace data. operation is one of get_job, get_client_history, get_connects_balance, search_jobs, list_messages; parameters contains the operation arguments.",
            "arguments": ["operation", "parameters"],
        },
        {
            "name": "portfolio_read",
            "description": "Read portfolio data. operation is get_case_study or list_skills; parameters contains the operation arguments.",
            "arguments": ["operation", "parameters"],
        },
        {
            "name": "workspace_read",
            "description": "Read workspace data. operation is free_slots; parameters contains days.",
            "arguments": ["operation", "parameters"],
        },
    ]
    prompt = (ROOT / "agent/prompts/tool_selection.v1.md").read_text()
    rows = []
    async with httpx.AsyncClient(timeout=90) as client:
        for design, tools in [("fine", fine), ("coarse", coarse), ("rewritten", rewritten)]:
            for task in tasks:
                start = time.perf_counter()
                body = {
                    "model": "qwen2.5:1.5b",
                    "messages": [
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": json.dumps({"tools": tools, "task": task["task"]})},
                    ],
                    "stream": False,
                    "format": {
                        "type": "object",
                        "properties": {"tool": {"type": "string"}, "arguments": {"type": "object"}},
                        "required": ["tool", "arguments"],
                    },
                    "options": {"temperature": 0, "seed": 4016, "num_predict": 150},
                }
                try:
                    r = await client.post(os.getenv("OLLAMA_URL", "http://127.0.0.1:11434") + "/api/chat", json=body)
                    r.raise_for_status()
                    result = r.json()
                    out = json.loads(result["message"]["content"])
                    selected = out.get("tool")
                    args = out.get("arguments", {})
                    if design == "coarse":
                        operation = args.get("operation")
                        parameters = args.get("parameters", {})
                        expected_owner = (
                            "marketplace_read"
                            if task["expected"] in [x[0] for x in BASE[:5]]
                            else ("workspace_read" if task["expected"] == "free_slots" else "portfolio_read")
                        )
                        selection = selected == expected_owner and operation == task["expected"]
                        args = parameters
                    else:
                        selection = selected == task["expected"]
                    arguments = selection and args == task["arguments"]
                    rows.append(
                        {
                            "design": design,
                            "task_id": task["id"],
                            "selection_correct": selection,
                            "arguments_correct": arguments,
                            "tokens": result.get("prompt_eval_count", 0) + result.get("eval_count", 0),
                            "seconds": time.perf_counter() - start,
                            "output": out,
                        }
                    )
                except Exception as e:
                    rows.append(
                        {
                            "design": design,
                            "task_id": task["id"],
                            "selection_correct": False,
                            "arguments_correct": False,
                            "error": str(e),
                            "seconds": time.perf_counter() - start,
                        }
                    )
            print("tool design", design, "done", flush=True)
            save("tools", {"rows": rows, "status": "running"})
    summary = {
        d: {
            "n": 40,
            "selection_accuracy": sum(r["selection_correct"] for r in rows if r["design"] == d) / 40,
            "argument_accuracy": sum(r["arguments_correct"] for r in rows if r["design"] == d) / 40,
            "mean_tokens": float(np.mean([r.get("tokens", 0) for r in rows if r["design"] == d])),
            "p95_seconds": float(np.percentile([r["seconds"] for r in rows if r["design"] == d], 95)),
        }
        for d in ["fine", "coarse", "rewritten"]
    }
    return save(
        "tools",
        {
            "status": "complete",
            "model": "qwen2.5:1.5b",
            "summary": summary,
            "rows": rows,
            "limitations": [
                "Synthetic repeated tasks; limited linguistic diversity",
                "JSON tool selection, not native tool-call execution; actual schemas are separately tested through MCP",
            ],
        },
    )


if __name__ == "__main__":
    asyncio.run(run())
