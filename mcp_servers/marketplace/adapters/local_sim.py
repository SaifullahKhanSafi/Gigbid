"""Our own deterministic local mock, NOT the instructor's GigSim.

Synthetic reply/hire rules are published, so these outcomes test plumbing only.
They cannot establish marketplace effectiveness or official GigSim reply rates.
"""

import json
import time
import uuid
import os
from datetime import datetime, timezone
from core import db
from core.security import decode, digest, tenant
from core.settings import ROOT, policy


def jobs():
    return json.loads((ROOT / "data/processed/jobs.json").read_text(encoding="utf-8"))


def lock(conn, user):
    import os

    if os.getenv("DATABASE_URL"):
        conn.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (user,))
    else:
        conn.execute("BEGIN IMMEDIATE")


class LocalSimulator:
    async def search_jobs(self, query="", limit=20):
        data = jobs()
        words = query.lower().split()
        return {
            "jobs": [
                j for j in data if not words or any(w in (j["title"] + " " + j["description"]).lower() for w in words)
            ][:limit],
            "source": "local_synthetic_simulator",
        }

    async def get_job(self, job_id):
        custom = db.get(tenant(), "job", job_id)
        if custom:
            return custom
        result = next((j for j in jobs() if j["id"] == job_id), None)
        if result is None:
            raise ValueError("Unknown job")
        return result

    async def get_client_history(self, client_id):
        j = next((j for j in jobs() if j["client_id"] == client_id), None)
        return dict(j["client"] if j else {"spend": 0, "rating": 0, "hires": 0, "verified": False}, synthetic=True)

    async def get_connects_balance(self):
        return db.get(tenant(), "wallet", "balance") or {
            "balance": 120,
            "spent": 0,
            "week": datetime.now(timezone.utc).strftime("%G-%V"),
        }

    async def list_messages(self, conversation_id):
        return {"messages": [x for x in db.scan(tenant(), "message") if x["conversation_id"] == conversation_id]}

    async def create_proposal_draft(self, payload):
        return await self._write("create_proposal_draft", payload)

    async def submit_proposal(self, payload):
        return await self._write("submit_proposal", payload)

    async def send_message(self, payload):
        return await self._write("send_message", payload)

    async def _write(self, action, payload):
        user = tenant()
        payload = dict(payload)
        canonical = {k: v for k, v in payload.items() if k not in ("approval_token", "dry_run", "trace_id")}
        canonical["action"] = action
        body_hash = digest(canonical)
        job = await self.get_job(payload["job_id"]) if "job_id" in payload else None
        cost = (job["connects"] + policy()["connects_surcharge"]) if action == "submit_proposal" else 0
        preview = {
            "action": action,
            "payload": canonical,
            "connects_cost": cost,
            "payload_hash": body_hash,
            "destination": "local_synthetic_simulator",
            "requires_platform_confirmation": False,
        }
        if payload.get("dry_run", True):
            return dict(preview, dry_run=True)
        grant = decode(payload.get("approval_token", ""), "approved_write")
        if grant["sub"] != user or grant.get("hash") != body_hash:
            raise PermissionError("Human approval does not match this exact action and content")
        settings = db.get(user, "settings", "profile") or {}
        with db.connection() as c:
            lock(c, user)
            receipt = db.get(user, "receipt", payload["idempotency_key"], c)
            if receipt:
                if receipt["hash"] != body_hash:
                    raise ValueError("Idempotency key reused with different payload")
                return receipt["result"]
            week = datetime.now(timezone.utc).strftime("%G-%V")
            wallet = db.get(user, "wallet", "balance", c) or {"balance": 120, "spent": 0, "week": week}
            if wallet.get("week") != week:
                wallet["spent"] = 0
                wallet["week"] = week
            if (
                cost > policy()["max_connects_per_bid"]
                or cost > wallet["balance"]
                or cost + wallet["spent"] > settings.get("weekly_connects", 100)
            ):
                raise ValueError("Connects limit exceeded")
            wallet["balance"] -= cost
            wallet["spent"] += cost
            db.put(user, "wallet", "balance", wallet, c)
            result = {
                "id": uuid.uuid4().hex,
                "action": action,
                "status": "submitted" if action == "submit_proposal" else "drafted",
                "connects_spent": cost,
                "synthetic": True,
                "job_id": payload.get("job_id"),
                "conversation_id": payload.get("conversation_id", payload.get("job_id")),
                "text": payload["text"],
                "amount": payload.get("amount"),
                "screening_answers": payload.get("screening_answers", {}),
                "created": time.time(),
            }
            if action == "send_message":
                result.update(status="sent", sender="freelancer")
                db.put(user, "message", result["id"], result, c)
            else:
                db.put(user, "proposal", result["id"], result, c)
                if action == "submit_proposal":
                    fixture = (
                        os.getenv(
                            "GIGBID_CLIENT_MODE", "fixture" if os.getenv("GIGBID_MODEL_MODE") == "test" else "llm"
                        )
                        == "fixture"
                    )
                    if not fixture:
                        db.put(
                            user,
                            "simulated_client_task",
                            result["id"],
                            {"id": result["id"], "proposal_id": result["id"], "status": "queued"},
                            c,
                        )
                        result["local_client_pending"] = True
                    else:
                        reply = {
                            "id": uuid.uuid4().hex,
                            "conversation_id": payload["job_id"],
                            "sender": "client",
                            "text": "Thank you. Could you explain your validation plan and suggest an interview time?",
                            "created": time.time(),
                            "synthetic": True,
                        }
                        db.put(user, "message", reply["id"], reply, c)
                        result["local_fixture_reply"] = True
            db.put(user, "receipt", payload["idempotency_key"], {"hash": body_hash, "result": result}, c)
        return result
