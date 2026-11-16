import difflib
import time
from unittest.mock import patch
import yaml
from core.settings import policy
from agent.nodes.logic import quote
from evals.runners.common import save


def run():
    start = time.perf_counter()
    old = policy()
    new = dict(old, version="local-rehearsal-2", connects_surcharge=2)
    job = {"budget_min": 30, "budget_max": 60, "connects": 10}
    before = quote(job, 20, 40)
    with patch("agent.nodes.logic.policy", return_value=new):
        after = quote(job, 20, 40)
    diff = "\n".join(
        difflib.unified_diff(
            yaml.safe_dump(old).splitlines(),
            yaml.safe_dump(new).splitlines(),
            fromfile="local_policy.yaml",
            tofile="local_rehearsal.yaml",
        )
    )
    return save(
        "policy_rehearsal",
        {
            "status": "local rehearsal, not official November 2 update",
            "before_connects": before.connects,
            "after_connects": after.connects,
            "validation_seconds": time.perf_counter() - start,
            "engineering_edit_time": None,
            "production_source_files_changed": 0,
            "configuration_diff": diff,
            "official_update_result": None,
        },
    )


if __name__ == "__main__":
    run()
