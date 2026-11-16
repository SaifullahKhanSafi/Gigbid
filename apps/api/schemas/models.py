from typing import Literal
from pydantic import BaseModel, Field, ConfigDict, model_validator


class Credentials(BaseModel):
    email: str = Field(min_length=3, max_length=254, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    password: str = Field(min_length=8, max_length=128)


class Session(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str


class Profile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    persona: Literal["ml", "web", "data", "own"] = "ml"
    floor_rate: float = Field(default=20, ge=1, le=10000)
    weekly_connects: int = Field(default=100, ge=0, le=10000)
    saved_search: str = Field(default="", max_length=500)
    scheduled_scouting: bool = False
    autonomy: Literal["suggest", "auto_skip"] = "suggest"
    agency_mode: bool = False

    @model_validator(mode="after")
    def keep_real_profile_separate(self):
        if self.persona == "own" and self.agency_mode:
            raise ValueError("Own portfolio cannot be combined with fictional agency members")
        return self


class StartRun(BaseModel):
    job_id: str = Field(min_length=1, max_length=128)


class StartConversation(BaseModel):
    conversation_id: str = Field(min_length=1, max_length=128)


class RunRecord(BaseModel):
    id: str
    kind: str
    status: str
    job_id: str | None = None
    conversation_id: str | None = None
    state: dict = {}
    error: str | None = None
    created: float = 0
    updated: float = 0


class JobRecord(BaseModel):
    id: str
    title: str
    description: str
    skills: list[str]
    budget_min: float
    budget_max: float
    connects: int
    synthetic: bool
    run: RunRecord | None = None


class RunList(BaseModel):
    runs: list[RunRecord]


class JobList(BaseModel):
    jobs: list[JobRecord]


class Health(BaseModel):
    status: str
    marketplace: str
    mode: str
    model_mode: str
    official_assets: bool = False
