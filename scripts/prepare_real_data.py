"""Clean the licensed 2024 job snapshot and derive hourly pricing from train records only."""

import hashlib
import html
import json
import re
import numpy as np
import pandas as pd
from core.settings import ROOT
from core.security import mask
from evals.runners.common import save

SOURCE = "https://www.kaggle.com/datasets/asaniczka/upwork-job-postings-dataset-2024-50k-records"
LICENSE = "ODC Attribution License (ODC-By) 1.0"
CATEGORIES = {
    "ml": r"\b(?:machine learning|pytorch|rag|artificial intelligence|nlp|computer vision|tensorflow)\b",
    "web": r"\b(?:react|next\.js|django|fastapi|full.?stack|node\.js|web development)\b",
    "data": r"\b(?:data analy|tableau|power bi|dbt|snowflake|data warehouse|data science|sql)\b",
}


def run():
    raw = ROOT / "data/raw/upwork-job-postings-dataset-2024-50k-records/upwork-jobs.csv"
    df = pd.read_csv(raw)
    start = len(df)
    rows = []
    seen = set()
    duplicate = invalid = masked = 0
    for original in df.fillna("").to_dict("records"):
        title = html.unescape(str(original["title"])).strip()
        description = html.unescape(str(original["description"]))
        description = re.sub(r"<[^>]+>", " ", description)
        description = re.sub(r"\s+", " ", description).strip()
        # Original job ID survives RSS query variants; never keep a client/contact identifier.
        link = str(original["link"])
        match = re.search(r"_(?:%7E|~)([\w]+)", link)
        normalized = re.sub(r"\s+", " ", title + " " + description).casefold()
        identity = match.group(1) if match else normalized
        key = hashlib.sha256(identity.encode()).hexdigest()
        if key in seen:
            duplicate += 1
            continue
        if len(title) < 3 or len(description) < 40:
            invalid += 1
            continue
        seen.add(key)
        safe = mask(description)
        masked += int(safe != description)
        skills = []
        skill_block = re.search(r"Skills:(.*?)(?:Skills:|Country:|click to apply|$)", description)
        if skill_block:
            skills = list(dict.fromkeys(s.strip() for s in skill_block.group(1).split(",") if 1 < len(s.strip()) < 80))

        def numeric(k):
            try:
                value = float(original[k])
                return value if np.isfinite(value) and value > 0 else None
            except (ValueError, TypeError):
                return None

        hourly = str(original["is_hourly"]).lower() == "true"
        lower, upper = numeric("hourly_low"), numeric("hourly_high")
        category = next(
            (p for p, pattern in CATEGORIES.items() if re.search(pattern, title + " " + description, re.I)), "other"
        )
        rows.append(
            {
                "id": key,
                "title": mask(title),
                "description": safe,
                "skills": skills,
                "published_date": str(original["published_date"]),
                "budget_type": "hourly" if hourly else "fixed",
                "hourly_low": lower,
                "hourly_high": upper,
                "fixed_budget": numeric("budget"),
                "category": category,
                "synthetic": False,
                "source": SOURCE,
                "license": LICENSE,
                "currency": "USD inferred from dataset dollar notation",
                "client_history": None,
                "connects": None,
                "provenance": "asaniczka; historical third-party Upwork snapshot, Feb 2024; not collected by GigBid",
            }
        )
    rows.sort(key=lambda r: (r["published_date"], r["id"]))
    cut = int(len(rows) * 0.8)
    for n, row in enumerate(rows):
        row["split"] = "train" if n < cut else "holdout"
    folder = ROOT / "data/processed"
    folder.mkdir(exist_ok=True)
    (folder / "real_jobs.jsonl").write_text("".join(json.dumps(x) + "\n" for x in rows), encoding="utf-8")
    statistics = {}
    for category in ["all", "ml", "web", "data"]:
        subset = [r for r in rows[:cut] if category == "all" or r["category"] == category]
        values = []
        for r in subset:
            if r["budget_type"] != "hourly":
                continue
            lo, hi = r["hourly_low"], r["hourly_high"]
            if lo and hi and hi < lo:
                continue
            midpoint = (lo + hi) / 2 if lo and hi else lo or hi
            if midpoint and 1 <= midpoint <= 500:
                values.append(midpoint)
        statistics[category] = {
            "hourly_usd_median": float(np.median(values)) if values else None,
            "n_hourly": len(values),
            "q25": float(np.percentile(values, 25)) if values else None,
            "q75": float(np.percentile(values, 75)) if values else None,
        }
    artifact = {
        "source": SOURCE,
        "license": LICENSE,
        "train_records": cut,
        "holdout_records": len(rows) - cut,
        "categories": statistics,
        "method": "80/20 chronological split; positive hourly midpoint/one available bound; reversed bands and rates outside USD 1-500 excluded; fixed budgets never pooled with hourly rates",
    }
    (folder / "market_stats.json").write_text(json.dumps(artifact, indent=2))
    result = save(
        "real_data",
        {
            "dataset": "Kaggle 2024 Upwork snapshot; real third-party historical records",
            "source": SOURCE,
            "license": LICENSE,
            "raw_csv_sha256": hashlib.sha256(raw.read_bytes()).hexdigest(),
            "input_rows": start,
            "output_rows": len(rows),
            "duplicates_removed": duplicate,
            "invalid_removed": invalid,
            "rows_pii_masked": masked,
            "market_statistics": artifact,
            "limitations": [
                "Third-party collection provenance, not independently audited",
                "Historical posted budgets, not actual negotiated rates or freelancer earnings",
                "No ground-truth fit/risk/proposal outcomes",
                "Skills parsed from noisy RSS description; missing skills remain empty",
                "Temporal holdout used for data isolation, not labelled quality evaluation",
                "Do not infer client histories or Connects costs from absent fields",
            ],
        },
    )
    print(json.dumps({k: v for k, v in result.items() if k != "limitations"}, indent=2))


if __name__ == "__main__":
    run()
