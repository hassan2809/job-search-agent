from sqlalchemy import select
from sqlalchemy.orm import Session


def filter_new_records(db: Session, model, records: list[dict]) -> list[dict]:
    """Filters out records whose (source, external_id) already exists for the given model."""
    if not records:
        return []

    keys = {(r["source"], r["external_id"]) for r in records}
    existing_rows = db.execute(
        select(model.source, model.external_id).where(
            model.source.in_({k[0] for k in keys}),
            model.external_id.in_({k[1] for k in keys}),
        )
    ).all()
    existing_keys = {(row.source, row.external_id) for row in existing_rows}

    return [r for r in records if (r["source"], r["external_id"]) not in existing_keys]
