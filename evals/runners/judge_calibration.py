"""Import real human labels; never auto-fill them with a model or synthetic gold."""

import argparse
import csv
from sklearn.metrics import cohen_kappa_score
from evals.runners.common import save


def run(path):
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    labelled = [r for r in rows if r.get("human_label") and r.get("judge_label")]
    if len(labelled) < 30:
        raise ValueError("Need at least 30 independently human-labelled items with judge labels")
    return save(
        "judge_calibration",
        {
            "n": len(labelled),
            "cohen_kappa": cohen_kappa_score(
                [r["human_label"] for r in labelled], [r["judge_label"] for r in labelled]
            ),
            "rows": labelled,
        },
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("csv")
    run(p.parse_args().csv)
