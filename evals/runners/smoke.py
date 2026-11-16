"""CI metrics on 30 fixed synthetic jobs with explicit regression thresholds."""

from evals.runners.decision_eval import run
from rag.verify import verify

if __name__ == "__main__":
    result = run(30, output_name="smoke_decisions")
    assert result["summary"]["all"]["bid_f1"] >= 0.9, "Bid/skip F1 regression"
    item = {"id": "check", "text": "Built a Python API.", "approved_claims": ["Built a Python API."]}
    checked = verify("I have 100 years of experience. [check]\nBuilt a Python API. [check]", [item])
    assert all(c.status in ("supported", "non_experience") for c in verify(checked.text, [item]).claims), (
        "Unsupported-claim regression"
    )
    print("30-job smoke gate passed.")
