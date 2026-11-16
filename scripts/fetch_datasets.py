"""Official Kaggle API acquisition. Refuses to ingest data without verified license metadata."""

import argparse
import hashlib
import json
import zipfile
import httpx
from core.settings import ROOT

SOURCES = [
    "asaniczka/upwork-job-postings-dataset-2024-50k-records",
    "asaniczka/all-jobs-on-upwork-200k-plus",
    "ahmedmyalo/upwork-freelance-jobs-60k",
    "asaniczka/freelance-contracts-dataset-1-3-million-entries",
    "sarveshchhetri/freelancer-success-earnings-and-churn-prediction",
    "adityammantri/trial-1",
]


def fetch(slug, download=False):
    dest = ROOT / "data/raw" / slug.split("/")[-1]
    dest.mkdir(parents=True, exist_ok=True)
    status = {"slug": slug, "url": "https://www.kaggle.com/datasets/" + slug, "used": False}
    try:
        with httpx.Client(timeout=60, follow_redirects=True) as client:
            r = client.get("https://www.kaggle.com/api/v1/datasets/view/" + slug)
            status["metadata_http_status"] = r.status_code
            r.raise_for_status()
            meta = r.json()
            status["metadata"] = meta
            (dest / "metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
            license_value = meta.get("licenseName") or meta.get("licenses")
            if not license_value or str(license_value).casefold() in ("unknown", "other", "unspecified"):
                raise ValueError("License not verified. Obtain dataset-metadata.json from the owner/Kaggle.")
            status["license"] = license_value
            if download:
                r = client.get("https://www.kaggle.com/api/v1/datasets/download/" + slug)
                r.raise_for_status()
                archive = dest / "download.zip"
                archive.write_bytes(r.content)
                status["sha256"] = hashlib.sha256(r.content).hexdigest()
                with zipfile.ZipFile(archive) as z:
                    for member in z.infolist():
                        target = (dest / member.filename).resolve()
                        if not target.is_relative_to(dest.resolve()):
                            raise ValueError("Unsafe archive path")
                    z.extractall(dest)
                status["downloaded"] = True
    except Exception as e:
        status["error"] = str(e)
    return status


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--download", action="store_true")
    p.add_argument("--slug", choices=SOURCES)
    args = p.parse_args()
    records = [fetch(s, args.download) for s in ([args.slug] if args.slug else SOURCES)]
    out = ROOT / "evals/results/data_acquisition.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    previous = json.loads(out.read_text()) if out.exists() else []
    merged = {r["slug"]: r for r in previous}
    for record in records:
        old = merged.get(record["slug"], {})
        for key in ("downloaded", "sha256", "used"):
            if key not in record or key == "used":
                if key in old:
                    record[key] = old[key]
        merged[record["slug"]] = record
    out.write_text(json.dumps(list(merged.values()), indent=2), encoding="utf-8")
    print(json.dumps([{k: v for k, v in r.items() if k != "metadata"} for r in records], indent=2))
