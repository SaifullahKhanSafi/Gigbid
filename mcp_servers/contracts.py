"""Declared output contracts are retained even when negotiated MCP omits outputSchema."""

from pydantic import BaseModel, ConfigDict, Field


class Output(BaseModel):
    model_config = ConfigDict(extra="allow")


class JobOutput(Output):
    id: str
    title: str
    description: str
    skills: list[str]
    budget_min: float = Field(ge=0)
    budget_max: float = Field(ge=0)


class JobsOutput(Output):
    jobs: list[JobOutput]


class HistoryOutput(Output):
    spend: float = Field(ge=0)
    rating: float = Field(ge=0, le=5)
    hires: int = Field(ge=0)
    verified: bool


class BalanceOutput(Output):
    balance: int = Field(ge=0)
    spent: int = Field(default=0, ge=0)


class MessagesOutput(Output):
    messages: list[dict]


class EvidenceOutput(Output):
    id: str
    persona: str
    type: str
    text: str
    source: str
    date: str
    project: str
    skills: list[str]
    synthetic: bool
    outcome: str | None = None


class EvidenceSearchOutput(Output):
    items: list[EvidenceOutput]


class SkillsOutput(Output):
    skills: dict[str, int]


class WriteOutput(Output):
    action: str
    dry_run: bool = False
    connects_cost: int | None = Field(default=None, ge=0)
    connects_spent: int = Field(default=0, ge=0)
    payload_hash: str | None = None
    payload: dict | None = None
    id: str | None = None
    status: str | None = None


class SlotsOutput(Output):
    slots: list[dict]
    synthetic: bool
    timezone: str


class TeamRankOutput(Output):
    selected_persona: str
    fit: dict
    member_scores: dict[str, float]


class WorkspaceDraftOutput(Output):
    payload_hash: str
    dry_run: bool = False
    payload: dict | None = None
