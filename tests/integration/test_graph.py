import uuid
import pytest
from mcp.shared.memory import create_connected_server_and_client_session
from contextlib import AsyncExitStack
from core import db
from core.security import tenant_context
from agent.mcp_client import ALLOWLISTS, OWNER
from agent.graphs.bid_graph import build_bid_graph
from agent.graphs.conversation_graph import build_conversation_graph
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.types import Command
from core.settings import RUNTIME


class MemoryGateway:
    def __init__(self):
        self.stack = AsyncExitStack()
        self.sessions = {}

    async def __aenter__(self):
        from importlib import import_module

        for owner in ("marketplace", "portfolio", "workspace"):
            server = import_module("mcp_servers." + owner + ".server").mcp
            self.sessions[owner] = await self.stack.enter_async_context(
                create_connected_server_and_client_session(server)
            )
        return self

    async def __aexit__(self, *args):
        return await self.stack.__aexit__(*args)

    async def call(self, role, name, **args):
        assert name in ALLOWLISTS[role]
        owner = OWNER[name]
        if owner not in self.sessions:
            from importlib import import_module

            server = import_module("mcp_servers." + owner + ".server").mcp
            self.sessions[owner] = await self.stack.enter_async_context(
                create_connected_server_and_client_session(server)
            )
        result = await self.sessions[owner].call_tool(name, args)
        if result.isError:
            raise ValueError(str(result.content))
        import json

        return result.structuredContent or json.loads(result.content[0].text)


@pytest.mark.asyncio
async def test_approval_restart_exactly_once_and_conversation():
    user = "graph-" + uuid.uuid4().hex
    tenant_context.set(user)
    db.put(user, "settings", "profile", {"persona": "ml", "floor_rate": 20, "weekly_connects": 100})
    cfg = {"configurable": {"thread_id": user}, "recursion_limit": 40}
    path = str(RUNTIME / (user + ".sqlite3"))
    async with MemoryGateway() as gw, AsyncSqliteSaver.from_conn_string(path) as saver:
        graph = build_bid_graph(gw, saver, {"persona": "ml", "floor_rate": 20})
        state = await graph.ainvoke(
            {
                "tenant": user,
                "job_id": "demo-ml-0001",
                "persona": "ml",
                "trace_id": user,
                "steps": 0,
                "tokens": 0,
                "events": [],
            },
            cfg,
        )
        assert "__interrupt__" in state
        assert not db.scan(user, "proposal")
        assert (await graph.aget_state(cfg)).values["status"] == "awaiting_approval"
    # New saver, graph and MCP sessions simulate a process restart at approval.
    async with MemoryGateway() as gw, AsyncSqliteSaver.from_conn_string(path) as saver:
        graph = build_bid_graph(gw, saver, {"persona": "ml", "floor_rate": 20})
        result = await graph.ainvoke(Command(resume={"action": "approve"}), cfg)
        assert result["status"] == "submitted"
        assert len(db.scan(user, "proposal")) == 1
        receipt = db.scan(user, "receipt")[0]
        before = db.get(user, "wallet", "balance")
        # Replaying the dispatch task with the exact authorization cannot spend twice.
        req = {
            "idempotency_key": "proposal-" + user,
            "job_id": "demo-ml-0001",
            "text": result["draft"]["text"],
            "amount": result["price"]["amount"],
            "screening_answers": result["draft"].get("screening_answers", {}),
            "approval_token": result["approval_token"],
            "dry_run": False,
            "trace_id": user,
        }
        again = await gw.call("dispatch", "submit_proposal", request=req)
        assert again["id"] == receipt["result"]["id"] and db.get(user, "wallet", "balance") == before
        conversation = build_conversation_graph(gw, saver)
        ccfg = {"configurable": {"thread_id": user + ":conversation"}}
        reply = await conversation.ainvoke(
            {"tenant": user, "trace_id": user + "-conversation", "conversation_id": "demo-ml-0001", "events": []}, ccfg
        )
        assert "__interrupt__" in reply
        sent = await conversation.ainvoke(Command(resume={"action": "approve"}), ccfg)
        assert sent["status"] == "sent"


@pytest.mark.asyncio
async def test_scam_is_skipped():
    user = "scam-" + uuid.uuid4().hex
    tenant_context.set(user)
    db.put(user, "settings", "profile", {"persona": "ml"})
    async with MemoryGateway() as gw, AsyncSqliteSaver.from_conn_string(":memory:") as saver:
        graph = build_bid_graph(gw, saver, {"persona": "ml", "floor_rate": 20})
        out = await graph.ainvoke(
            {"tenant": user, "job_id": "demo-ml-0000", "trace_id": user, "steps": 0, "tokens": 0, "events": []},
            {"configurable": {"thread_id": user}},
        )
        assert out["status"] == "skipped" and out["risk"]["injection"] and not db.scan(user, "proposal")


@pytest.mark.asyncio
async def test_crash_after_marketplace_commit_before_checkpoint_replays_once():
    class CrashGateway(MemoryGateway):
        async def call(self, role, name, **args):
            result = await super().call(role, name, **args)
            if role == "dispatch" and name == "submit_proposal":
                raise RuntimeError("Simulated process failure after committed side effect")
            return result

    user = "crash-window-" + uuid.uuid4().hex
    tenant_context.set(user)
    db.put(user, "settings", "profile", {"persona": "ml", "floor_rate": 20, "weekly_connects": 100})
    cfg = {"configurable": {"thread_id": user}, "recursion_limit": 40}
    path = str(RUNTIME / (user + ".sqlite3"))
    async with CrashGateway() as gateway, AsyncSqliteSaver.from_conn_string(path) as saver:
        graph = build_bid_graph(gateway, saver, {"persona": "ml", "floor_rate": 20})
        await graph.ainvoke(
            {
                "tenant": user,
                "trace_id": user,
                "job_id": "demo-ml-0001",
                "persona": "ml",
                "events": [],
                "steps": 0,
                "tokens": 0,
            },
            cfg,
        )
        with pytest.raises(Exception):
            await graph.ainvoke(Command(resume={"action": "approve"}), cfg)
        assert len(db.scan(user, "proposal")) == 1
        wallet = db.get(user, "wallet", "balance")
    async with MemoryGateway() as gateway, AsyncSqliteSaver.from_conn_string(path) as saver:
        graph = build_bid_graph(gateway, saver, {"persona": "ml", "floor_rate": 20})
        result = await graph.ainvoke(None, cfg)
        assert result["status"] == "submitted"
        assert len(db.scan(user, "proposal")) == 1 and len(db.scan(user, "message")) == 1
        assert db.get(user, "wallet", "balance") == wallet


@pytest.mark.asyncio
async def test_deleted_evidence_blocks_an_already_approved_draft():
    user = "deleted-" + uuid.uuid4().hex
    tenant_context.set(user)
    db.put(user, "settings", "profile", {"persona": "ml"})
    cfg = {"configurable": {"thread_id": user}}
    async with MemoryGateway() as gateway, AsyncSqliteSaver.from_conn_string(":memory:") as saver:
        graph = build_bid_graph(gateway, saver, {"persona": "ml", "floor_rate": 20})
        state = await graph.ainvoke(
            {"tenant": user, "trace_id": user, "job_id": "demo-ml-0001", "events": [], "steps": 0, "tokens": 0}, cfg
        )
        assert "__interrupt__" in state
        for item in state["fit"]["evidence"]:
            db.put(user, "deleted_evidence", item["id"], {"id": item["id"]})
        result = await graph.ainvoke(Command(resume={"action": "approve"}), cfg)
        assert result["status"] == "blocked" and not db.scan(user, "proposal")
