"""Only reads executed result files. Missing measurements remain explicitly unavailable."""

import json
from core.settings import ROOT


def read(name):
    p = ROOT / "evals/results" / f"{name}.json"
    return json.loads(p.read_text()) if p.exists() else None


def merge_architecture():
    initial = read("architectures")
    corrected = read("architecture_supervisor_corrected")
    if not initial or not corrected or corrected.get("status") != "complete":
        return initial
    if not initial.get("corrected_supervisor"):
        (ROOT / "evals/results/architectures_before_supervisor_schema_fix.json").write_text(
            json.dumps(initial, indent=2)
        )
        initial["rows"] = [r for r in initial["rows"] if r["architecture"] != "prebuilt_supervisor"] + corrected["rows"]
        initial["summary"]["prebuilt_supervisor"] = corrected["summary"]["prebuilt_supervisor"]
        initial["corrected_supervisor"] = (
            "Explicit outer structured state schema; rerun 50 identical jobs. Original failures retained separately."
        )
        initial["correction_source"] = "architecture_supervisor_corrected.json"
        (ROOT / "evals/results/architectures.json").write_text(json.dumps(initial, indent=2))
    return initial


def run():
    architecture = merge_architecture()
    lines = [
        "# Executed results",
        "",
        "These are local development measurements on explicitly synthetic labels unless the source is marked real. They are not official GigSim or hidden-test results. Paid API costs exclude hardware/electricity/hosting.",
        "",
        "## Retrieval",
        "",
        "Source: [retrieval.json](../evals/results/retrieval.json). Project-level gold; empty gold excluded from recall. Timings are retrieval only and include cached queries after initial calls.",
        "",
        "| Variant | Recall@5 | MRR | nDCG@10 | p95 seconds |",
        "|---|---:|---:|---:|---:|",
    ]
    r = read("retrieval")
    if r:
        for v, s in r["summary"].items():
            lines.append(
                f"| {v} | {s['recall_at_5']:.4f} | {s['mrr']:.4f} | {s['ndcg_at_10']:.4f} | {s['p95_seconds']:.4f} |"
            )
        lines.extend(
            [
                "",
                f"Selected: **{r['selected_variant']}**, provisionally. Synthetic template overlap inflates these scores. Cross-encoder reranking did not beat decomposition. Official reply rate and calibrated judge score: unavailable.",
            ]
        )
    lines.extend(
        [
            "",
            "## Tool design",
            "",
            "Source: [tools.json](../evals/results/tools.json). Forty synthetic tasks per design; JSON selection rather than native call execution.",
            "",
            "| Design | Selection accuracy | Argument accuracy | Mean tokens |",
            "|---|---:|---:|---:|",
        ]
    )
    r = read("tools")
    for v, s in (r or {}).get("summary", {}).items():
        lines.append(f"| {v} | {s['selection_accuracy']:.3f} | {s['argument_accuracy']:.3f} | {s['mean_tokens']:.1f} |")
    lines.extend(
        [
            "",
            "## Architecture comparison",
            "",
            "Source: [architectures.json](../evals/results/architectures.json). Same fifty jobs, uniform 1.5B model. Errors count as incorrect. Handwritten rules overlap synthetic gold; decision correctness does not imply an approved draft.",
            "",
            "| Architecture | Bid accuracy | Execution failure | Unsupported / completed job | p95 s | Tokens |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for v, s in (architecture or {}).get("summary", {}).items():
        u = s["unsupported_claims_per_completed_job"]
        u = f"{u:.3f}" if u is not None else "unavailable"
        lines.append(
            f"| {v} | {s['bid_accuracy']:.3f} | {s['execution_failure_rate']:.3f} | {u} | {s['p95_seconds']:.2f} | {s['total_tokens']} |"
        )
    if architecture:
        from collections import Counter

        counts = Counter(r.get("status", "error") for r in architecture["rows"] if r["architecture"] == "handwritten")
        lines.extend(
            [
                "",
                f"Handwritten graph terminal states on the uniform small-model run: `{dict(counts)}`. Needs-attention drafts were not sent. Supervisor schema integration failures were fixed and the same fifty jobs rerun; original records are retained. These systems differ in deterministic safeguards, so this is a product-system comparison rather than proof of a general multi-agent reasoning advantage.",
            ]
        )
    lines.extend(
        [
            "",
            "## Local models",
            "",
            "Source: [models.json](../evals/results/models.json). Thirty writer tasks per profile after explicit schemas. Unverified raw-plan sentences are conservatively rejected; that metric is not calibrated factual hallucination accuracy.",
            "",
            "| Profile | Valid JSON | Rejected raw sentences / plan | Final unsupported | p95 s | Generation tokens/s |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    r = read("models")
    for v, s in (r or {}).get("summary", {}).items():
        lines.append(
            f"| {v} | {s['valid_plan_rate']:.3f} | {s['raw_unsupported_per_plan']:.3f} | {s['final_unsupported_per_draft']:.3f} | {s['p95_seconds']:.2f} | {s['mean_generation_tokens_per_second']:.1f} |"
        )
    lines.extend(
        [
            "",
            "The schema fix improved the smallest model from the failed initial run in `models_before_schema_fix.json`. Both final writer configurations had valid structured output, but persuasive quality has not been independently rated. The 7B writer remains provisional; no human-quality superiority is claimed.",
            "",
            "## Decisions, data, safety and extension",
            "",
        ]
    )
    r = read("decisions")
    if r:
        s = r["summary"]["all"]
        lines.append(
            f"- [decisions.json](../evals/results/decisions.json): {s['jobs']} jobs; bid/skip F1 {s['bid_f1']:.3f}; scam precision/recall {s['scam_precision']:.3f}/{s['scam_recall']:.3f}; proposed price inside synthetic band {s['price_in_band']:.3f}. The price metric includes skipped low-budget jobs; rule-derived labels share definitions with guards."
        )
    r = read("real_data")
    if r:
        lines.append(
            f"- [real_data.json](../evals/results/real_data.json): real Kaggle snapshot, {r['input_rows']:,} input and {r['output_rows']:,} retained rows; {r['duplicates_removed']} duplicate and {r['invalid_removed']} invalid rows removed; {r['rows_pii_masked']} records changed by PII masking. Source/license and chronological split are documented in DATA_CARD."
        )
    r = read("agency")
    if r:
        lines.append(
            f"- [agency.json](../evals/results/agency.json): mean supported requirement coverage {r['mean_agency_coverage']:.3f} with routing, {r['mean_ml_only_coverage']:.3f} for ML-only assignment. Shared synthetic skill ontology limits generalization."
        )
    r = read("safety")
    if r:
        lines.append(
            f"- [safety.json](../evals/results/safety.json): detector flagged {r['detector_recall_on_attack_suite']:.1%} of a small attack suite. This is detector recall, not model jailbreak ASR. Deliberately fabricated claim probes went from {r['unsupported_before']} verifier-rejected claims to {r['unsupported_after']} remaining after removal."
        )
    lines.extend(
        [
            "",
            "## Unavailable measurements",
            "",
            "Official GigSim replies/hires, hidden results, independently human-calibrated judge scores, blind-panel preferences, actual November 2 policy adaptation and public deployment uptime are unavailable. Values remain null. No synthetic proxy is labelled as an official outcome.",
        ]
    )
    (ROOT / "docs/RESULTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    # Preserve actual failed dev jobs with IDs and specific measured failure categories.
    failures = []
    if architecture:
        for row in architecture["rows"]:
            if row.get("error") or not row["correct"] or row.get("unsupported_claims", 0):
                category = (
                    "tool_or_structured_output"
                    if row.get("error")
                    else ("wrong_decision" if not row["correct"] else "unverified_claim")
                )
                failures.append(
                    {
                        "job_id": row["job_id"],
                        "architecture": row["architecture"],
                        "category": category,
                        "observed": row.get("error")
                        or f"gold_bid={row['gold_bid']}, predicted_bid={row.get('pred_bid')}, rejected_claims={row.get('unsupported_claims', 0)}",
                        "source": "architectures.json",
                        "fix": "Explicit outer schema fixed integration errors; output-length/model failures remain counted. Conservative verification and deterministic risk/fit address unsafe drafts, with human review still required.",
                    }
                )
    (ROOT / "evals/results/failure_analysis.json").write_text(
        json.dumps(
            {
                "failures": failures,
                "note": "Actual failed synthetic dev executions, not invented cases; source rows retain text/errors.",
            },
            indent=2,
        )
    )
    print("Generated RESULTS.md and failure_analysis.json from executed results.")


if __name__ == "__main__":
    run()
