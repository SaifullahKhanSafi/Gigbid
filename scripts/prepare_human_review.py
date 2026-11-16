import csv
import json
from core.settings import ROOT


def main():
    models = json.loads((ROOT / "evals/results/models.json").read_text())
    records = [r for r in models["rows"] if r["profile"] == "open"][:30]
    folder = ROOT / "evals/datasets"
    with (folder / "human_calibration.csv").open("w", encoding="utf-8", newline="") as out:
        w = csv.DictWriter(out, fieldnames=["item_id", "job_id", "proposal_text", "human_label", "judge_label"])
        w.writeheader()
        for i, r in enumerate(records):
            w.writerow(
                {
                    "item_id": f"calibration-{i:02d}",
                    "job_id": r["job_id"],
                    "proposal_text": r.get("raw_plan", ""),
                    "human_label": "",
                    "judge_label": "",
                }
            )
    groups = {p: [r for r in models["rows"] if r["profile"] == p] for p in ["open", "open_small"]}
    with (folder / "blind_panel.csv").open("w", encoding="utf-8", newline="") as out:
        w = csv.DictWriter(
            out, fieldnames=["pair_id", "job_id", "proposal_A", "proposal_B", "rater_id", "preferred_A_B_tie", "reason"]
        )
        w.writeheader()
        for i in range(min(30, len(groups["open"]), len(groups["open_small"]))):
            a, b = groups["open"][i], groups["open_small"][i]
            if i % 2:
                a, b = b, a
            w.writerow(
                {
                    "pair_id": f"pair-{i:02d}",
                    "job_id": a["job_id"],
                    "proposal_A": a.get("raw_plan", ""),
                    "proposal_B": b.get("raw_plan", ""),
                }
            )
    (folder / "HUMAN_REVIEW.md").write_text(
        "# Human review protocol\n\nLabels are deliberately blank. These sheets compare model-generated plans, not complete deployed proposals; independently rate full proposals for the final assignment quality study. Read each job in synthetic_dev.json, then label support/partial/unsupported from the cited corpus. Do not look at automated verifier outputs first. Obtain separate judge labels, join by item ID, and run python -m evals.runners.judge_calibration evals/datasets/human_calibration.csv after at least 30 human labels.\n\nFor the blind panel, ask real classmates to choose A/B/tie and give a reason. Model order alternates; do not disclose it to raters. Never fill human cells with a model.\n"
    )
    print("Prepared blank 30-item human calibration and blind-plan review sheets.")


if __name__ == "__main__":
    main()
