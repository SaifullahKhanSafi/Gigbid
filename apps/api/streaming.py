import asyncio
import json
from core import db


async def stream_run(tenant, run_id, request):
    """Persisted LangGraph state/event replay survives refresh and worker restart."""
    last = None
    while not await request.is_disconnected():
        record = db.get(tenant, "run", run_id)
        if not record:
            return
        data = json.dumps(record, sort_keys=True)
        if data != last:
            yield "event: state\ndata: " + data + "\n\n"
            last = data
        else:
            yield ": heartbeat\n\n"
        if record["status"] in (
            "submitted",
            "sent",
            "skipped",
            "rejected",
            "blocked",
            "needs_attention",
            "awaiting_approval",
            "awaiting_platform_confirmation",
        ):
            yield "event: settled\ndata: {}\n\n"
            return
        await asyncio.sleep(0.5)
