import hashlib
import re
import json
from pathlib import Path
from core.security import mask


def load_document(path: Path, metadata: dict):
    """CV PDF, Markdown, source, JSON/text reviews and proposals share one metadata contract."""
    required = {"persona", "type", "project", "skills", "date", "industry", "synthetic", "provenance"}
    if required - metadata.keys():
        raise ValueError(f"Missing metadata: {required - metadata.keys()}")
    if path.suffix.lower() == ".pdf":
        from pypdf import PdfReader

        text = "\n".join(p.extract_text() or "" for p in PdfReader(path).pages)
    else:
        text = path.read_text(encoding="utf-8")
    if not text.strip():
        raise ValueError("Empty document or scanned PDF requiring OCR")
    text = mask(text)
    return dict(
        metadata,
        id=hashlib.sha256(
            json.dumps(
                {
                    "text": text,
                    "persona": metadata["persona"],
                    "type": metadata["type"],
                    "project": metadata["project"],
                },
                sort_keys=True,
            ).encode()
        ).hexdigest()[:24],
        text=text,
        source=path.name,
        approved_claims=[],
    )


def chunks(item, words=110, overlap=20):
    tokens = item["text"].split()
    return [
        dict(item, chunk_id=f"{item['id']}:{n}", text=" ".join(tokens[n : n + words]))
        for n in range(0, len(tokens), words - overlap)
    ]


def normalize_csv(path, source, license_name):
    """Real job normalization is explicit; missing fields remain unknown rather than invented."""
    import pandas as pd

    if not license_name:
        raise ValueError("A verified license is required")
    df = pd.read_csv(path).fillna("")
    aliases = {
        "title": ["title", "job_title", "jobTitle"],
        "description": ["description", "job_description", "jobDescription"],
        "skills": ["skills", "tags"],
        "budget_min": ["hourly_low", "hourly_rate_from", "budget_min"],
        "budget_max": ["hourly_high", "hourly_rate_to", "budget", "budget_max"],
    }
    seen = set()
    jobs = []
    for row in df.to_dict("records"):
        item = {
            k: next((row[x] for x in names if x in row and str(row[x]).strip()), "") for k, names in aliases.items()
        }
        normalized = re.sub(r"\s+", " ", str(item["title"]) + " " + str(item["description"])).strip()
        if len(normalized) < 40:
            continue
        key = hashlib.sha256(normalized.lower().encode()).hexdigest()
        if key in seen:
            continue
        seen.add(key)
        jobs.append(
            dict(
                item,
                id=key,
                description=mask(str(item["description"])),
                synthetic=False,
                provenance=source,
                license=license_name,
                source_record_sha256=key,
            )
        )
    return jobs
