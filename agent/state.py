import operator
from typing import Annotated, TypedDict


class BidState(TypedDict, total=False):
    tenant: str
    job_id: str
    persona: str
    trace_id: str
    job: dict
    spec: dict
    risk: dict
    fit: dict
    decision: dict
    price: dict
    draft: dict
    critique: dict
    compliance: dict
    preview: dict
    approval: dict
    approval_token: str
    outcome: dict
    revision: int
    status: str
    error: str
    steps: Annotated[int, operator.add]
    tokens: Annotated[int, operator.add]
    events: Annotated[list[dict], operator.add]


class ConversationState(TypedDict, total=False):
    tenant: str
    conversation_id: str
    trace_id: str
    messages: list[dict]
    intent: str
    draft: str
    slots: list[dict]
    preview: dict
    approval: dict
    approval_token: str
    outcome: dict
    status: str
    events: Annotated[list[dict], operator.add]
