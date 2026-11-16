import uuid
from fastapi.testclient import TestClient
from apps.api.main import app
from core import db


def test_connected_feed_uses_mcp_and_caches_only_tenant_records(monkeypatch):
    calls = []

    class Gateway:
        def __init__(self, user, trace):
            self.user = user

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def call(self, role, name, **args):
            calls.append((self.user, role, name, args))
            return {
                "jobs": [
                    {
                        "id": "mapped-live-job",
                        "title": "Live mapped job",
                        "description": "A verified adapter-normalized job description.",
                        "skills": ["Python"],
                        "budget_min": 30,
                        "budget_max": 50,
                        "connects": 12,
                    }
                ]
            }

    monkeypatch.setattr("agent.mcp_client.ToolGateway", Gateway)
    monkeypatch.setattr("apps.api.routers.routes.config", lambda: {"marketplace": {"mode": "upwork"}})
    with TestClient(app) as client:
        login = client.post(
            "/api/auth/register", json={"email": uuid.uuid4().hex + "@example.test", "password": "contract-test123"}
        ).json()
        response = client.get("/api/jobs", headers={"Authorization": "Bearer " + login["access_token"]})
        assert response.status_code == 200
        assert len(response.json()["jobs"]) == 1 and response.json()["jobs"][0]["synthetic"] is False
        assert calls[0][1:3] == ("scout", "search_jobs")
        assert db.get(login["user_id"], "job", "mapped-live-job")
        assert not db.get("other-tenant", "job", "mapped-live-job")
