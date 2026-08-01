from datetime import datetime

from pydantic import BaseModel, ConfigDict


class LeadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source: str
    external_id: str
    title: str
    description: str
    url: str
    author: str
    contact_email: str | None
    is_manual: bool
    origin_type: str
    posted_at: datetime | None
    fetched_at: datetime
    latest_verdict: str | None = None
    latest_outreach_status: str | None = None


class LeadManualIn(BaseModel):
    url: str
    raw_content: str | None = None
    # Matches the form's default and ORIGIN_GUIDANCE's fallback in app/services/outreach.py --
    # origin_type changes how the outreach message is framed, so the two ends must not disagree.
    origin_type: str = "prospected"  # disclosed_need | prospected
    author: str = ""


class IngestResult(BaseModel):
    fetched: int
    inserted: int
    skipped_duplicates: int


class LeadListOut(BaseModel):
    items: list[LeadOut]
    total: int
