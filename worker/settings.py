import os
from arq import cron
from arq.connections import RedisSettings
from worker.runner import execute_run as run_graph


async def execute_run(ctx, tenant, run_id):
    """Arq retries degraded work; the local worker has its own durable lease loop."""
    from arq import Retry
    from core import db

    await run_graph(ctx, tenant, run_id)
    record = db.get(tenant, "run", run_id)
    if record and record["status"] == "queued_retry":
        if ctx.get("job_try", 1) >= 5:
            record.update(
                status="needs_attention",
                error="Marketplace unavailable after bounded retries; retry from the run viewer.",
            )
            db.put(tenant, "run", run_id, record)
        else:
            raise Retry(defer=min(60, 2 ** ctx.get("job_try", 1) * 5))
    task = db.get(tenant, "task", run_id)
    if task:
        task.update(state="done", lease_until=0)
        db.put(tenant, "task", run_id, task)


async def scheduled_scout(ctx):
    """Saved searches are tenant-scoped; four-hour polling avoids aggressive live access."""
    from core import db
    from agent.mcp_client import ToolGateway
    from apps.api.service import create_run
    import time

    with db.connection() as c:
        rows = db.execute(c, "SELECT tenant,body FROM documents WHERE kind='settings' AND id='profile'").fetchall()
    for row in rows:
        tenant = row["tenant"]
        profile = db.get(tenant, "settings", "profile")
        if not profile.get("scheduled_scouting"):
            continue
        async with ToolGateway(tenant, "schedule-" + str(int(time.time()))) as gateway:
            result = await gateway.call("scout", "search_jobs", query=profile.get("saved_search", ""), limit=5)
        for job in result.get("jobs", []):
            await create_run(tenant, job["id"])


async def simulated_client_recovery(ctx):
    from support.simulated_clients import process_all_pending

    await process_all_pending()


class WorkerSettings:
    functions = [execute_run]
    cron_jobs = [
        cron(scheduled_scout, hour={0, 4, 8, 12, 16, 20}, minute=5),
        cron(simulated_client_recovery, minute=set(range(60)), second=30),
    ]
    redis_settings = RedisSettings.from_dsn(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    job_timeout = 600
    max_jobs = 2
    max_tries = 5
