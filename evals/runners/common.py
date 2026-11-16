import json
import platform
from datetime import datetime, timezone
import numpy as np
from core.settings import ROOT


def dataset(limit=None):
    items = json.loads((ROOT / "evals/datasets/synthetic_dev.json").read_text())
    if limit:
        groups = {p: [v for v in items if v["persona"] == p] for p in ["ml", "web", "data"]}
        return [groups[p][n] for n in range((limit + 2) // 3) for p in groups][:limit]
    return items


def metrics(retrieved, gold):
    gold = set(gold)
    top = retrieved[:5]
    if not gold:
        return None
    hits = [int(x in gold) for x in retrieved]
    recall = len(set(top) & gold) / len(gold)
    mrr = next((1 / (i + 1) for i, h in enumerate(hits) if h), 0)
    dcg = sum(h / np.log2(i + 2) for i, h in enumerate(hits[:10]))
    idcg = sum(1 / np.log2(i + 2) for i in range(min(len(gold), 10)))
    return {"recall_at_5": recall, "mrr": mrr, "ndcg_at_10": dcg / idcg}


def mean(rows, key):
    vals = [r[key] for r in rows if r.get(key) is not None]
    return float(np.mean(vals)) if vals else None


def save(name, result):
    import torch

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": "synthetic_dev; NOT official GigSim",
        "hardware": {
            "platform": platform.platform(),
            "torch": torch.__version__,
            "cuda": torch.cuda.is_available(),
            "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        },
        **result,
    }
    folder = ROOT / "evals/results"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / (name + ".json")).write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result
