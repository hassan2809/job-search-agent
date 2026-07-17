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


class LeadManualIn(BaseModel):
    url: str
    raw_content: str
    origin_type: str = "disclosed_need"  # disclosed_need | prospected
    author: str = ""


class IngestResult(BaseModel):
    fetched: int
    inserted: int
    skipped_duplicates: int
