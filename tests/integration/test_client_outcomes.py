import pytest
import uuid
from core import db
from core.security import tenant_context, token
from agent.handoffs import WriteRequest
from mcp_servers.marketplace.adapters.local_sim import LocalSimulator
from support.simulated_clients import process_pending


@pytest.mark.asyncio
async def test_llm_client_queue_and_replay_create_one_reply(monkeypatch):
    user = "client-queue-" + uuid.uuid4().hex
    tenant_context.set(user)
    monkeypatch.setenv("GIGBID_CLIENT_MODE", "llm")
    adapter = LocalSimulator()
    req = WriteRequest(
        idempotency_key="client-" + user, job_id="demo-ml-0001", text="I would validate a sample first.", amount=75
    ).model_dump()
    preview = await adapter.submit_proposal(req)
    req.update(dry_run=False, approval_token=token(user, "approved_write", hash=preview["payload_hash"]))
    result = await adapter.submit_proposal(req)
    assert result["local_client_pending"] and not db.scan(user, "message")

    async def fake_judge(*args, **kwargs):
        return {
            "stage": "interview",
            "reason": "Relevant evidence",
            "message": "Could we discuss the validation plan?",
            "synthetic": True,
            "seconds": 0.1,
            "model": "test-client",
        }

    monkeypatch.setattr("support.simulated_clients.judge_proposal", fake_judge)
    await process_pending(user)
    await process_pending(user)
    assert len(db.scan(user, "message")) == 1
    assert db.scan(user, "simulated_client_outcome")[0]["stage"] == "interview"
