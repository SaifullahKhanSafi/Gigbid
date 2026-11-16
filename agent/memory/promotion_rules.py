import difflib
from collections import Counter
from core import db
from core.security import digest, mask
from core.settings import config
from agent.memory.store import MemoryStore


def record_edit(tenant, before, after, event_id):
    """Only authenticated user edits count; three independent repeated deletions promote style."""
    if db.get(tenant, "edit", event_id):
        return
    removed = []
    for line in difflib.ndiff(before.splitlines(), after.splitlines()):
        if line.startswith("- "):
            removed.append(mask(line[2:])[:300])
    db.put(
        tenant,
        "edit",
        event_id,
        {
            "id": event_id,
            "removed": removed,
            "diff": mask("\n".join(difflib.unified_diff(before.splitlines(), after.splitlines()))),
        },
    )
    counts = Counter(line for e in db.scan(tenant, "edit") for line in set(e["removed"]))
    for sentence, n in counts.items():
        if n >= config()["memory"]["style_min_confirmations"]:
            key = digest(sentence)[:20]
            MemoryStore().put(
                (tenant, "style"),
                key,
                {
                    "rule": "Avoid this sentence: " + sentence,
                    "confirmations": n,
                    "source": "repeated authenticated user deletions",
                },
            )


def record_outcome(tenant, category, outcome, event_id):
    if outcome not in ("won", "replied", "ignored"):
        raise ValueError("Unknown outcome")
    if db.get(tenant, "outcome_observation", event_id):
        return
    db.put(tenant, "outcome_observation", event_id, {"id": event_id, "category": category, "outcome": outcome})
    observations = [x for x in db.scan(tenant, "outcome_observation") if x["category"] == category]
    n = len(observations)
    positive = sum(x["outcome"] in ("won", "replied") for x in observations)
    threshold = config()["memory"]
    if n >= threshold["outcome_min_observations"] and positive / n >= threshold["outcome_min_reply_rate"]:
        MemoryStore().put(
            (tenant, "outcome"),
            category,
            {
                "category": category,
                "observations": n,
                "reply_or_win_rate": positive / n,
                "source": "observed outcomes only; correlation, not causation",
            },
        )
