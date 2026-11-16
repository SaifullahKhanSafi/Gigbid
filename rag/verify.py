"""Conservative extractive verifier. No semantic entailment claims are invented.

Experience sentences must be exact approved facts or verbatim corpus quotations,
with valid citations. Novel paraphrases are marked partly supported and removed.
This trades recall and prose fluency for a reviewable grounding guarantee.
"""

import re
from agent.handoffs import Claim, ProposalDraft

EXPERIENCE = re.compile(
    r"\b(?:built|delivered|developed|implemented|worked|experience|years|achieved|improved|increased|reduced|certified|expert|speciali[sz]|led|managed|created|trained|deployed|proven|successfully|i have|we have|my portfolio)\b",
    re.I,
)
CITATION = re.compile(r"\[([a-zA-Z0-9:_-]+)\]")


def sentences(text):
    return [s.strip() for s in re.split(r"\n+|(?<=[.!?])\s+(?=[A-Z])", text) if s.strip()]


def normalize(text):
    return re.sub(r"\s+", " ", text.strip().strip('"\u201c\u201d')).casefold().rstrip(".")


def check_claim(sentence, evidence):
    cited = CITATION.findall(sentence)
    clean = CITATION.sub("", sentence).strip()
    by_id = {e["id"]: e for e in evidence}
    known = [by_id[i] for i in cited if i in by_id]
    exact = False
    for item in known:
        allowed = item.get("approved_claims", []) + [item["text"]]
        if any(normalize(clean) == normalize(f) for f in allowed):
            exact = True
        if clean.startswith("Portfolio excerpt:"):
            excerpt = clean[len("Portfolio excerpt:") :].strip().strip('"\u201c\u201d')
            if excerpt and excerpt in item["text"]:
                exact = True
    if cited and (not known or len(known) != len(cited)):
        return Claim(
            text=sentence,
            evidence_ids=cited,
            status="unsupported",
            reason="Citation does not resolve in this tenant/persona retrieval",
        )
    if exact:
        return Claim(
            text=sentence,
            evidence_ids=cited,
            status="supported",
            reason="Exact fact or verbatim excerpt from cited evidence",
        )
    if EXPERIENCE.search(clean) or re.search(r"\b\d+(?:\.\d+)?\s*(?:%|years|clients|projects)\b", clean, re.I):
        return Claim(
            text=sentence,
            evidence_ids=cited,
            status="partly_supported" if known else "unsupported",
            reason="Novel experience wording requires human evidence review",
        )
    # Even non-past-tense factual assertions can fabricate credentials. Permit only a
    # deliberately small grammar of plans and questions; abstain on all other prose.
    if re.match(
        r"(?i)^(?:I (?:would|can|propose|suggest)|My proposed approach|Could you|What |Would you|Thank you|Hello|Hi\b|For this project|Proposed rate|Availability|Please confirm)",
        clean,
    ):
        return Claim(
            text=sentence,
            evidence_ids=cited,
            status="non_experience",
            reason="Forward-looking plan or question; no portfolio fact asserted",
        )
    return Claim(
        text=sentence,
        evidence_ids=cited,
        status="unsupported",
        reason="Unverified assertion outside allowed planning grammar",
    )


def verify(text, evidence, version=1):
    claims = [check_claim(s, evidence) for s in sentences(text)]
    kept = [c.text for c in claims if c.status in ("supported", "non_experience")]
    return ProposalDraft(text="\n".join(kept), claims=claims, version=version)
