from datetime import datetime

from pydantic import BaseModel, ConfigDict


class JobPostingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source: str
    external_id: str
    title: str
    company: str
    location: str
    description: str
    url: str
    posted_at: datetime | None
    fetched_at: datetime


class IngestResult(BaseModel):
    fetched: int
    inserted: int
    skipped_duplicates: int
