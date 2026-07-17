from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.lead import Lead
from app.schemas.lead import IngestResult, LeadManualIn, LeadOut
from app.services import excel_import
from app.utils.dedupe import filter_new_records
from app.utils.text import derive_title, extract_self_disclosed_email

router = APIRouter()


@router.post("/manual", response_model=LeadOut)
def add_manual_lead(lead_in: LeadManualIn, db: Session = Depends(get_db)) -> Lead:
    existing = db.execute(
        select(Lead).where(Lead.source == "linkedin_manual", Lead.external_id == lead_in.url)
    ).scalar_one_or_none()
    if existing:
        return existing

    lead = Lead(
        source="linkedin_manual",
        external_id=lead_in.url,
        title=derive_title(lead_in.raw_content),
        description=lead_in.raw_content,
        url=lead_in.url,
        author=lead_in.author,
        contact_email=extract_self_disclosed_email(lead_in.raw_content),
        is_manual=True,
        origin_type=lead_in.origin_type,
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


@router.post("/bulk-import", response_model=IngestResult)
async def bulk_import_leads(file: UploadFile, db: Session = Depends(get_db)) -> IngestResult:
    file_bytes = await file.read()
    try:
        parsed_leads = excel_import.parse_leads_xlsx(file_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    new_leads = filter_new_records(db, Lead, parsed_leads)
    for lead in new_leads:
        db.add(Lead(**lead))
    db.commit()

    return IngestResult(
        fetched=len(parsed_leads),
        inserted=len(new_leads),
        skipped_duplicates=len(parsed_leads) - len(new_leads),
    )


@router.get("", response_model=list[LeadOut])
def list_leads(limit: int = 50, db: Session = Depends(get_db)) -> list[Lead]:
    return list(db.execute(select(Lead).order_by(Lead.fetched_at.desc()).limit(limit)).scalars())
