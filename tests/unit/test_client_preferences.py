import pytest
from support.simulated_clients import preferences


def test_client_preferences_are_repeatable_and_independent_of_gold():
    job = {"id": "client-test", "skills": ["Python", "RAG", "FastAPI"], "budget_min": 30, "budget_max": 60}
    one = preferences(job)
    assert one == preferences(dict(job, gold_bid=False, persona_hint="data"))
    assert set(one["must_have_skills"]) <= set(job["skills"])
    assert 30 <= one["hourly_ceiling"] <= 60


@pytest.mark.asyncio
async def test_client_budget_gate_overrules_llm_hire(monkeypatch):
    import httpx
    from support.simulated_clients import judge_proposal

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, *args, **kwargs):
            return httpx.Response(
                200,
                request=httpx.Request("POST", "http://local.test"),
                json={
                    "message": {"content": '{"stage":"hired","reason":"Relevant","message":"Let us begin"}'},
                    "prompt_eval_count": 12,
                    "eval_count": 10,
                },
            )

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: FakeClient())
    job = {"id": "over-budget", "skills": ["Python"], "budget_min": 20, "budget_max": 30}
    result = await judge_proposal(job, "I would test.", 100, [])
    assert result["stage"] == "ignored" and result["message"] == ""
