from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.lead import Lead
from app.models.match import Match
from app.models.outreach import Outreach
from app.schemas.lead import IngestResult, LeadListOut, LeadManualIn, LeadOut
from app.services import excel_import
from app.utils.dedupe import filter_new_records
from app.utils.text import derive_title, extract_self_disclosed_email

router = APIRouter()

FIT_STATUSES = {"good_fit", "maybe", "not_a_fit", "not_checked"}

OUTREACH_STATUSES = {
    "not_started",
    "connection_drafted",
    "connection_sent",
    "connection_accepted",
    "connection_declined",
    "connection_no_response",
    "message_drafted",
    "awaiting_reply",
    "replied",
    "closed_won",
    "closed_declined",
    "closed_no_response",
    "closed_not_interested",
}


def _attach_latest_verdicts(db: Session, leads: list[Lead]) -> dict[int, str]:
    """Newest Match per lead_id, keyed by lead_id -- leads.py's own fit-check re-run guard means
    there's usually just one, but force=true can create more, so take the newest."""
    if not leads:
        return {}
    lead_ids = [lead.id for lead in leads]
    matches = list(
        db.execute(select(Match).where(Match.lead_id.in_(lead_ids)).order_by(Match.created_at.desc())).scalars()
    )
    latest_verdict: dict[int, str] = {}
    for match in matches:
        latest_verdict.setdefault(match.lead_id, match.fit_verdict)
    return latest_verdict


def _attach_latest_outreach_statuses(db: Session, leads: list[Lead]) -> dict[int, str]:
    """Newest Outreach.status per lead_id -- a lead can only have one active Outreach at a time
    in practice, but take the newest if more than one exists."""
    if not leads:
        return {}
    lead_ids = [lead.id for lead in leads]
    outreaches = list(
        db.execute(select(Outreach).where(Outreach.lead_id.in_(lead_ids)).order_by(Outreach.created_at.desc())).scalars()
    )
    latest_status: dict[int, str] = {}
    for outreach in outreaches:
        latest_status.setdefault(outreach.lead_id, outreach.status)
    return latest_status


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


@router.get("", response_model=LeadListOut)
def list_leads(
    limit: int = 20,
    offset: int = 0,
    origin_type: str | None = None,
    fit_status: str | None = None,
    outreach_status: str | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
) -> LeadListOut:
    if fit_status is not None and fit_status not in FIT_STATUSES:
        raise HTTPException(status_code=400, detail=f"fit_status must be one of: {', '.join(sorted(FIT_STATUSES))}")
    if outreach_status is not None and outreach_status not in OUTREACH_STATUSES:
        raise HTTPException(
            status_code=400, detail=f"outreach_status must be one of: {', '.join(sorted(OUTREACH_STATUSES))}"
        )

    statement = select(Lead).order_by(Lead.fetched_at.desc())
    if origin_type:
        statement = statement.where(Lead.origin_type == origin_type)
    if search:
        pattern = f"%{search}%"
        statement = statement.where(or_(Lead.title.ilike(pattern), Lead.description.ilike(pattern)))
    all_matching = list(db.execute(statement).scalars())

    latest_verdict = _attach_latest_verdicts(db, all_matching)
    if fit_status:
        if fit_status == "not_checked":
            all_matching = [lead for lead in all_matching if lead.id not in latest_verdict]
        else:
            all_matching = [lead for lead in all_matching if latest_verdict.get(lead.id) == fit_status]

    latest_outreach_status = _attach_latest_outreach_statuses(db, all_matching)
    if outreach_status:
        if outreach_status == "not_started":
            all_matching = [lead for lead in all_matching if lead.id not in latest_outreach_status]
        else:
            all_matching = [lead for lead in all_matching if latest_outreach_status.get(lead.id) == outreach_status]

    total = len(all_matching)
    items = all_matching[offset : offset + limit]
    for lead in items:
        lead.latest_verdict = latest_verdict.get(lead.id)  # type: ignore[attr-defined]
        lead.latest_outreach_status = latest_outreach_status.get(lead.id)  # type: ignore[attr-defined]
    return LeadListOut(items=items, total=total)


@router.get("/{lead_id}", response_model=LeadOut)
def get_lead(lead_id: int, db: Session = Depends(get_db)) -> Lead:
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    lead.latest_verdict = _attach_latest_verdicts(db, [lead]).get(lead.id)  # type: ignore[attr-defined]
    lead.latest_outreach_status = _attach_latest_outreach_statuses(db, [lead]).get(lead.id)  # type: ignore[attr-defined]
    return lead
