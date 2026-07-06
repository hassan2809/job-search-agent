import logging

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.job_posting import JobPosting
from app.schemas.job import IngestResult, JobPostingOut
from app.services.sources import arbeitnow, remoteok
from app.utils.dedupe import filter_new_postings

logger = logging.getLogger(__name__)
router = APIRouter()

SOURCES = [remoteok, arbeitnow]


@router.post("/ingest", response_model=IngestResult)
def ingest_jobs(db: Session = Depends(get_db)) -> IngestResult:
    fetched: list[dict] = []
    for source_module in SOURCES:
        try:
            fetched.extend(source_module.fetch_postings())
        except Exception:
            logger.exception("failed_to_fetch_from_source", extra={"source": source_module.__name__})

    new_postings = filter_new_postings(db, fetched)
    for posting in new_postings:
        db.add(JobPosting(**posting))
    db.commit()

    return IngestResult(
        fetched=len(fetched),
        inserted=len(new_postings),
        skipped_duplicates=len(fetched) - len(new_postings),
    )


@router.get("", response_model=list[JobPostingOut])
def list_jobs(limit: int = 50, db: Session = Depends(get_db)) -> list[JobPosting]:
    return list(db.execute(select(JobPosting).order_by(JobPosting.fetched_at.desc()).limit(limit)).scalars())
