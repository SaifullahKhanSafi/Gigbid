import uuid
from fastapi.testclient import TestClient
from apps.api.main import app


def test_own_portfolio_upload_isolated_and_incremental_without_fake_credentials():
    with TestClient(app) as client:
        login = client.post(
            "/api/auth/register", json={"email": uuid.uuid4().hex + "@example.test", "password": "own-test-pass123"}
        ).json()
        headers = {"Authorization": "Bearer " + login["access_token"]}
        assert (
            client.put("/api/profile", headers=headers, json={"persona": "own", "agency_mode": True}).status_code == 422
        )
        assert client.put("/api/profile", headers=headers, json={"persona": "own"}).status_code == 200
        assert client.get("/api/evidence", headers=headers).json()["items"] == []
        assert len(client.get("/api/jobs", headers=headers).json()["jobs"]) == 36
        text = b"Built a Python API with FastAPI for a local test project. Delivery included API integration tests."
        data = {"kind": "case_study", "skills": "Python,FastAPI", "industry": "services"}
        one = client.post(
            "/api/portfolio/upload", headers=headers, data=data, files={"file": ("my-case.md", text, "text/markdown")}
        )
        two = client.post(
            "/api/portfolio/upload", headers=headers, data=data, files={"file": ("my-case.md", text, "text/markdown")}
        )
        assert one.status_code == 200 and two.json()["id"] == one.json()["id"]
        items = client.get("/api/evidence", headers=headers).json()["items"]
        assert len(items) == 1 and items[0]["persona"] == "own" and items[0]["skills"] == ["Python", "FastAPI"]
        assert items[0]["source"] == "my-case.md" and not items[0]["synthetic"]
