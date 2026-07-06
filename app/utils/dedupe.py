from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.job_posting import JobPosting


def filter_new_postings(db: Session, postings: list[dict]) -> list[dict]:
    if not postings:
        return []

    keys = {(p["source"], p["external_id"]) for p in postings}
    existing_rows = db.execute(
        select(JobPosting.source, JobPosting.external_id).where(
            JobPosting.source.in_({k[0] for k in keys}),
            JobPosting.external_id.in_({k[1] for k in keys}),
        )
    ).all()
    existing_keys = {(row.source, row.external_id) for row in existing_rows}

    return [p for p in postings if (p["source"], p["external_id"]) not in existing_keys]
