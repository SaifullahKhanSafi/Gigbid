from typing import Literal
from pydantic import BaseModel, Field, ConfigDict


class Handoff(BaseModel):
    model_config = ConfigDict(extra="forbid")


class JobSpec(Handoff):
    title: str
    deliverables: list[str]
    skills: list[str]
    budget_min: float = Field(ge=0)
    budget_max: float = Field(ge=0)
    timeline: str = "To confirm"
    screening_questions: list[str] = []
    hidden_needs: list[str] = []


class RiskReport(Handoff):
    score: float = Field(ge=0, le=1)
    scam: bool
    injection: bool
    flags: list[str]
    client_quality: float = Field(ge=0, le=1)


class FitReport(Handoff):
    score: float = Field(ge=0, le=1)
    matrix: list[dict]
    evidence: list[dict]
    missing: list[str]
    persona: str | None = None


class BidDecision(Handoff):
    action: Literal["bid", "watch", "skip"]
    reasons: list[str]


class PriceQuote(Handoff):
    amount: float = Field(gt=0)
    currency: Literal["USD"] = "USD"
    connects: int = Field(ge=0, le=100)
    rationale: str
    viable: bool


class Claim(Handoff):
    text: str
    evidence_ids: list[str] = []
    status: Literal["supported", "partly_supported", "unsupported", "non_experience"] = "unsupported"
    reason: str = ""


class ProposalDraft(Handoff):
    text: str
    claims: list[Claim] = []
    screening_answers: dict[str, str] = {}
    version: int = 1


class Critique(Handoff):
    passed: bool
    issues: list[str]
    revision: int = Field(ge=0, le=2)


class ComplianceVerdict(Handoff):
    allowed: bool
    violations: list[str]
    policy_version: str


class Approval(Handoff):
    action: Literal["approve", "edit", "reject"]
    text: str | None = Field(default=None, max_length=12000)
    reason: str = Field(default="", max_length=1000)


class WriteRequest(Handoff):
    idempotency_key: str = Field(min_length=12, max_length=128)
    job_id: str = Field(min_length=1, max_length=128)
    text: str = Field(min_length=1, max_length=12000)
    amount: float = Field(gt=0, le=1000000)
    screening_answers: dict[str, str] = Field(default_factory=dict, max_length=20)
    approval_token: str = ""
    dry_run: bool = True
    trace_id: str = Field(default="local", max_length=128)


class MessageRequest(Handoff):
    idempotency_key: str = Field(min_length=12, max_length=128)
    conversation_id: str = Field(min_length=1, max_length=128)
    text: str = Field(min_length=1, max_length=12000)
    approval_token: str = ""
    dry_run: bool = True
    trace_id: str = Field(default="local", max_length=128)
