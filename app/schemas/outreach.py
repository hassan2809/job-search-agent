from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lead_id: int
    fit_verdict: str
    fit_reasoning: str
    created_at: datetime


class OutreachMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    outreach_id: int
    sender: str
    body: str
    created_at: datetime


class OutreachOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lead_id: int
    match_id: int | None
    origin_type: str
    status: str
    message_count: int
    created_at: datetime
    updated_at: datetime


class OutreachDetailOut(OutreachOut):
    messages: list[OutreachMessageOut]


class NeedsNextMessageOut(OutreachOut):
    lead_title: str
    days_since_last_message: int


class ConnectionResponseIn(BaseModel):
    status: str  # accepted | declined | no_response


class ReplyIn(BaseModel):
    body: str  # a single new message, or a full pasted thread to sync retroactively


class CloseIn(BaseModel):
    status: str  # closed_won | closed_declined | closed_no_response
