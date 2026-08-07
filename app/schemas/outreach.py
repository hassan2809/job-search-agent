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
    # Rules this draft still breaks after the retry. Empty for clean drafts and for anything the
    # lead sent. Populated from the draft_checks row, so the UI can mark a draft worth editing.
    check_failures: list[dict] = []


class CheckStatRow(BaseModel):
    code: str
    first_attempt: int  # times this rule broke on the first draft
    unresolved: int  # times it survived the retry into the stored draft


class CheckStatsOut(BaseModel):
    drafts: int
    clean_first_time: int
    retried: int
    retry_fixed_all: int
    still_broken: int
    by_rule: list[CheckStatRow]


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


class ReviseIn(BaseModel):
    instruction: str


class CloseIn(BaseModel):
    status: str  # closed_won | closed_declined | closed_no_response | closed_not_interested
