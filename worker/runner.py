"""Arq task entry and local durable-queue worker share the exact same run function."""

import asyncio
from contextlib import asynccontextmanager
import os
import time
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.types import Command
from core import db
from core.settings import RUNTIME, config
from core.security import mask
from agent.mcp_client import ToolGateway, MarketplaceUnavailable
from agent.graphs.bid_graph import build_bid_graph
from agent.graphs.conversation_graph import build_conversation_graph
from agent.memory.promotion_rules import record_edit, record_outcome
from agent.memory.store import MemoryStore


@asynccontextmanager
async def checkpoints():
    if os.getenv("CHECKPOINT_DATABASE_URL"):
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

        async with AsyncPostgresSaver.from_conn_string(os.environ["CHECKPOINT_DATABASE_URL"]) as saver:
            await saver.setup()
            yield saver
    else:
        async with AsyncSqliteSaver.from_conn_string(str(RUNTIME / "checkpoints.sqlite3")) as saver:
            yield saver


def persist(tenant, run_id, state, status=None):
    record = db.get(tenant, "run", run_id) or {"id": run_id}
    # Approval grants are never surfaced to the browser or logs.
    public = {k: v for k, v in state.items() if k != "approval_token"}
    record.update(
        state=public, status=status or state.get("status", "running"), error=state.get("error"), updated=time.time()
    )
    db.put(tenant, "run", run_id, record)


async def execute_run(ctx, tenant, run_id):
    record = db.get(tenant, "run", run_id)
    if not record:
        return
    profile = db.get(tenant, "settings", "profile") or {"persona": "ml", "floor_rate": 20, "weekly_connects": 100}
    from core.settings import ROOT
    import json

    market = ROOT / "data/processed/market_stats.json"
    if market.exists():
        stats = json.loads(market.read_text())["categories"]
        profile["market_median"] = (stats.get(profile["persona"]) or stats["all"]).get("hourly_usd_median") or 45
    profile["style_memory"] = [x.value for x in MemoryStore().search((tenant, "style"))]
    resume = record.get("pending_approval")
    try:
        async with ToolGateway(tenant, run_id) as gateway, checkpoints() as saver:
            graph = (
                build_conversation_graph(gateway, saver)
                if record["kind"] == "conversation"
                else build_bid_graph(gateway, saver, profile)
            )
            cfg = {
                "configurable": {"thread_id": tenant + ":" + run_id},
                "recursion_limit": config()["budgets"]["max_graph_steps"],
            }
            snapshot = await graph.aget_state(cfg)
            previous_draft = snapshot.values.get("draft")
            if resume:
                value = Command(resume=resume)
            elif snapshot.values:
                if not snapshot.next:
                    persist(tenant, run_id, snapshot.values)
                    return
                if snapshot.interrupts:
                    persist(tenant, run_id, snapshot.values, "awaiting_approval")
                    return
                value = None
            else:
                value = {
                    "tenant": tenant,
                    "trace_id": run_id,
                    "persona": profile["persona"],
                    "job_id": record.get("job_id"),
                    "conversation_id": record.get("conversation_id"),
                    "steps": 0,
                    "tokens": 0,
                    "events": [],
                }
            persist(tenant, run_id, snapshot.values, "running")
            start = time.perf_counter()
            async for state in graph.astream(value, cfg, stream_mode="values"):
                clean = {k: v for k, v in state.items() if k != "__interrupt__"}
                if "__interrupt__" in state:
                    clean["interrupt"] = [x.value for x in state["__interrupt__"]]
                    clean["status"] = "awaiting_approval"
                persist(tenant, run_id, clean, "awaiting_approval" if "__interrupt__" in state else "running")
            final = await graph.aget_state(cfg)
            state = dict(final.values)
            if final.interrupts:
                state["interrupt"] = [x.value for x in final.interrupts]
                state["status"] = "awaiting_approval"
            state["execution_seconds"] = time.perf_counter() - start
            persist(tenant, run_id, state)
            if resume and resume["action"] == "edit" and previous_draft and state.get("status") == "awaiting_approval":
                before = previous_draft["text"] if isinstance(previous_draft, dict) else previous_draft
                record_edit(
                    tenant,
                    before,
                    resume.get("text", ""),
                    run_id
                    + ":"
                    + str(previous_draft.get("version", 1) if isinstance(previous_draft, dict) else time.time()),
                )
            if state.get("outcome", {}).get("local_fixture_reply"):
                record_outcome(
                    tenant, state.get("job", {}).get("industry", "general"), "replied", state["outcome"]["id"]
                )
            if state.get("outcome", {}).get("local_client_pending"):
                from support.simulated_clients import process_pending

                await process_pending(tenant)
            latest = db.get(tenant, "run", run_id)
            latest.pop("pending_approval", None)
            db.put(tenant, "run", run_id, latest)
            if state.get("events"):
                for event in state["events"]:
                    db.audit(tenant, run_id, event)
    except Exception as e:
        latest = db.get(tenant, "run", run_id) or record
        latest.update(
            status="queued_retry" if isinstance(e, MarketplaceUnavailable) else "needs_attention",
            error=mask(str(e))[:1000],
            updated=time.time(),
        )
        db.put(tenant, "run", run_id, latest)
        db.audit(tenant, run_id, {"error": str(e), "type": type(e).__name__})
        if os.getenv("GIGBID_RAISE_ERRORS") == "1":
            raise


async def enqueue(tenant, run_id):
    db.put(
        tenant,
        "task",
        run_id,
        {"id": run_id, "tenant": tenant, "run_id": run_id, "state": "queued", "lease_until": 0, "attempts": 0},
    )
    if os.getenv("REDIS_URL"):
        from arq import create_pool
        from arq.connections import RedisSettings

        pool = await create_pool(RedisSettings.from_dsn(os.environ["REDIS_URL"]))
        await pool.enqueue_job("execute_run", tenant, run_id, _job_id=tenant + ":" + run_id + ":" + str(time.time_ns()))
        await pool.aclose()


async def local_worker():
    """No web-request agent runs. Durable queue leases recover interrupted tasks."""
    while True:
        with db.connection() as c:
            rows = db.execute(c, "SELECT tenant,id,body FROM documents WHERE kind='task'").fetchall()
        claimed = False
        for row in rows:
            tenant = row["tenant"]
            key = row["id"]
            from mcp_servers.marketplace.adapters.local_sim import lock

            with db.connection() as c:
                lock(c, "worker-queue")
                task = db.get(tenant, "task", key, c)
                if task["state"] == "done" or task["lease_until"] > time.time():
                    continue
                task.update(state="running", lease_until=time.time() + 600, attempts=task.get("attempts", 0) + 1)
                db.put(tenant, "task", key, task, c)
            claimed = True
            await execute_run({}, tenant, task["run_id"])
            run = db.get(tenant, "run", task["run_id"])
            retry = run["status"] == "queued_retry" and task["attempts"] < 5
            task.update(state="queued" if retry else "done", lease_until=time.time() + 60 if retry else 0)
            db.put(tenant, "task", key, task)
        if not claimed:
            if os.getenv("GIGBID_MODEL_MODE") != "test":
                from support.simulated_clients import process_all_pending

                await process_all_pending()
            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(local_worker())
