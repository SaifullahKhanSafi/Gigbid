import time
import uuid
from core import db
from worker.runner import enqueue


async def create_run(tenant, job_id=None, conversation_id=None):
    kind = "conversation" if conversation_id else "bid"
    object_id = conversation_id or job_id
    index_key = kind + ":" + object_id
    from mcp_servers.marketplace.adapters.local_sim import lock

    with db.connection() as c:
        lock(c, "create-run:" + tenant)
        existing = db.get(tenant, "run_index", index_key, c)
        if existing:
            run = db.get(tenant, "run", existing["run_id"], c)
            if run and run["status"] not in ("rejected", "blocked", "skipped", "sent", "needs_attention"):
                return run
        run_id = uuid.uuid4().hex
        record = {
            "id": run_id,
            "kind": kind,
            "job_id": job_id,
            "conversation_id": conversation_id,
            "status": "queued",
            "state": {},
            "created": time.time(),
            "updated": time.time(),
        }
        db.put(tenant, "run", run_id, record, c)
        db.put(tenant, "run_index", index_key, {"run_id": run_id}, c)
    await enqueue(tenant, run_id)
    return record
