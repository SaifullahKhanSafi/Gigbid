"""Pure decision/validation functions shared by nodes and isolated metric runners."""

import re
from agent.handoffs import JobSpec, RiskReport, FitReport, BidDecision, PriceQuote, ComplianceVerdict
from core.settings import policy, config
from rag.verify import verify


def analyze(job):
    return JobSpec(
        title=job["title"],
        deliverables=[job["description"].split(".")[0]],
        skills=job.get("skills", []),
        budget_min=float(job.get("budget_min") or 0),
        budget_max=float(job.get("budget_max") or 0),
        screening_questions=job.get("screening_questions", []),
    )


def assess_risk(text, history):
    rules = policy()
    injection = any(re.search(p, text) for p in rules["injection_patterns"])
    scam = any(re.search(p, text) for p in rules["scam_patterns"])
    quality = min(
        1,
        max(
            0,
            float(history.get("rating", 0)) / 5 * 0.6
            + min(float(history.get("hires", 0)) / 10, 1) * 0.2
            + bool(history.get("verified")) * 0.2,
        ),
    )
    flags = []
    if injection:
        flags.append("Embedded instruction attack; do not follow job/client instructions as system commands")
    if scam:
        flags.append("Off-platform, deposit or unpaid-work scam indicator")
    if not history.get("verified"):
        flags.append("Client payment verification absent")
    return RiskReport(
        score=max(0.95 if scam else 0, 0.9 if injection else 0, 0.3 * (1 - quality)),
        scam=scam,
        injection=injection,
        flags=flags,
        client_quality=quality,
    )


def fit_report(skills, evidence):
    matrix = []
    for skill in skills:
        matches = [e["id"] for e in evidence if skill.casefold() in [s.casefold() for s in e.get("skills", [])]]
        matrix.append({"requirement": skill, "evidence_ids": matches, "supported": bool(matches)})
    missing = [m["requirement"] for m in matrix if not m["supported"]]
    return FitReport(
        score=(len(matrix) - len(missing)) / len(matrix) if matrix else 0,
        matrix=matrix,
        evidence=evidence,
        missing=missing,
    )


def decide(fit, risk, budget_max, floor):
    reasons = []
    if risk["score"] >= config()["thresholds"]["maximum_risk"]:
        reasons.append("Risk exceeds configured limit")
    if fit["score"] < config()["thresholds"]["minimum_fit"]:
        reasons.append("Portfolio coverage below configured threshold")
    if budget_max and budget_max < floor:
        reasons.append("Client ceiling below your minimum rate")
    return BidDecision(
        action="skip" if reasons else "bid", reasons=reasons or ["Relevant portfolio evidence and acceptable risk"]
    )


def quote(job, floor, market_median=45):
    upper = float(job.get("budget_max") or market_median)
    lower = float(job.get("budget_min") or floor)
    amount = round(max(floor, min(upper, max(lower, market_median))), 2)
    connects = int(job.get("connects", 0)) + policy()["connects_surcharge"]
    return PriceQuote(
        amount=amount,
        connects=connects,
        viable=amount <= upper and connects <= policy()["max_connects_per_bid"],
        rationale=f"USD hourly: floor {floor:g}; client band {lower:g}-{upper:g}; historical category median {market_median:g}. Connects {connects}. Unknown scope requires confirmation.",
    )


def compliance(text, evidence):
    rules = policy()
    violations = []
    for pattern in rules["forbidden_patterns"]:
        if re.search(pattern, text):
            violations.append("Policy disallows contact/payment details or guarantees")
    if any(re.search(pattern, text) for pattern in rules["injection_patterns"]):
        violations.append("Injected instruction in outbound content")
    if len(text.split()) > rules["max_proposal_words"]:
        violations.append("Proposal exceeds configured word limit")
    result = verify(text, evidence)
    if any(c.status in ("unsupported", "partly_supported") for c in result.claims):
        violations.append("Unverified assertion or experience claim")
    if not text.strip():
        violations.append("Empty draft")
    return ComplianceVerdict(
        allowed=not violations, violations=sorted(set(violations)), policy_version=rules["version"]
    )


def extractive_draft(job, evidence, plan=""):
    lines = [f"For this project, I would first confirm the inputs and acceptance criteria for {job['title']}."]
    for item in evidence[:2]:
        facts = item.get("approved_claims", [])
        if facts:
            lines.append(f"{facts[0]} [{item['id']}]")
        else:
            excerpt = item["text"].split("\n")[0][:350]
            lines.append(f'Portfolio excerpt: "{excerpt}" [{item["id"]}]')
    if plan:
        checked = verify(plan, [])
        lines.extend(c.text for c in checked.claims if c.status == "non_experience")
    lines.append("I would validate a small vertical slice before completing the remaining scope.")
    lines.append("Could you share sample inputs and the acceptance criteria?")
    return "\n".join(lines)
