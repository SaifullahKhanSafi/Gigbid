import uuid
from fastapi.testclient import TestClient
from apps.api.main import app
from core import db


def auth(client):
    email = uuid.uuid4().hex + "@example.test"
    response = client.post("/api/auth/register", json={"email": email, "password": "test-password-123"})
    assert response.status_code == 200
    return response.json(), {"Authorization": "Bearer " + response.json()["access_token"]}


def test_tenant_isolation_and_onboarding():
    with TestClient(app) as client:
        one, h1 = auth(client)
        two, h2 = auth(client)
        p = client.put("/api/profile", headers=h1, json={"persona": "data", "floor_rate": 30, "weekly_connects": 50})
        assert p.status_code == 200 and p.json()["persona"] == "data"
        assert client.get("/api/profile", headers=h2).json()["persona"] == "ml"
        db.put(
            one["user_id"],
            "run",
            "private",
            {"id": "private", "kind": "bid", "status": "awaiting_approval", "state": {}},
        )
        assert client.get("/api/runs/private", headers=h2).status_code == 404
        assert client.post("/api/runs/private/approval", headers=h2, json={"action": "approve"}).status_code == 404
        assert client.post("/api/runs/private/approval", headers=h1, json={"action": "reject"}).status_code == 422
        assert client.get("/api/jobs").status_code == 401
