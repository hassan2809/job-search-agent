from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.database import SessionLocal, get_db
from app.models.lead import Lead
from app.models.match import Match
from app.models.outreach import Outreach
from app.schemas.lead import IngestResult, LeadContactEmailIn, LeadListOut, LeadManualIn, LeadOut
from app.services import excel_import
from app.utils.dedupe import filter_new_records
from app.utils.text import derive_title, extract_self_disclosed_email

router = APIRouter()

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SCRAPE_SCRIPT = PROJECT_ROOT / "scripts" / "scrape_leads.py"
CLEAN_SCRIPT = PROJECT_ROOT / "scripts" / "clean_descriptions.py"

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
    "closed_seen_no_reply",
    "closed_not_seen",
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


def _title_from_url(url: str) -> str:
    path = unquote(urlparse(url).path).strip("/")
    slug = path.split("/")[-1] if path else ""
    if slug:
        return slug.replace("-", " ").strip() or "Pending profile"
    return "Pending profile"


def _sqlite_database_path() -> Path:
    db_url = settings.database_url
    if not db_url.startswith("sqlite:///"):
        raise RuntimeError("Manual scrape currently supports sqlite DATABASE_URL only.")
    return (PROJECT_ROOT / db_url.removeprefix("sqlite:///")).resolve()


def _run_script(script: Path, lead_id: int, *, label: str) -> str:
    if not script.exists():
        raise RuntimeError(f"{label} script not found: {script}")

    completed = subprocess.run(
        [
            sys.executable,
            str(script),
            "--database",
            str(_sqlite_database_path()),
            "--lead-id",
            str(lead_id),
        ],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    output = "\n".join(part for part in (completed.stdout, completed.stderr) if part).strip()
    if completed.returncode != 0:
        raise RuntimeError(output or f"{script.name} exited with code {completed.returncode}")
    return output


def _run_scrape_script(lead_id: int) -> None:
    output = _run_script(SCRAPE_SCRIPT, lead_id, label="Scrape")
    lowered = output.lower()
    if "stopped at lead" in lowered or "linkedin requires login" in lowered:
        raise RuntimeError(output)
    if f"failed lead {lead_id}" in lowered:
        raise RuntimeError(output)


def _run_clean_script(lead_id: int) -> None:
    _run_script(CLEAN_SCRIPT, lead_id, label="Clean")


def _finalize_scraped_profile(lead_id: int) -> Lead:
    with SessionLocal() as session:
        lead = session.get(Lead, lead_id)
        if not lead:
            raise RuntimeError(f"Lead {lead_id} not found after scrape.")
        if not (lead.description or "").strip():
            raise RuntimeError(
                f"Profile scrape produced no content for lead {lead_id}. "
                "Ensure LinkedIn is logged in via scripts/scrape_leads.py --login-only."
            )

        lead.title = derive_title(lead.description)
        lead.contact_email = extract_self_disclosed_email(lead.description)
        session.commit()
        session.refresh(lead)
        session.expunge(lead)
        return lead


def _fill_from_raw_content(lead: Lead, raw_content: str, lead_in: LeadManualIn) -> None:
    lead.title = derive_title(raw_content)
    lead.description = raw_content
    lead.contact_email = extract_self_disclosed_email(raw_content)
    lead.origin_type = lead_in.origin_type
    if lead_in.author:
        lead.author = lead_in.author


@router.post("/manual", response_model=LeadOut)
def add_manual_lead(lead_in: LeadManualIn, db: Session = Depends(get_db)) -> Lead:
    """Add a lead from a LinkedIn URL, scraping the profile unless raw_content is pasted in.

    A scrape can fail (LinkedIn login wall, verification prompt) after the row is already
    committed, which leaves a lead with no description. Re-posting the same URL therefore does NOT
    short-circuit on a contentless row -- it retries the scrape, or fills the row in from pasted
    raw_content. Only a lead that already has content counts as a duplicate. Without that, a single
    failed scrape would poison the URL forever: every retry would return the empty shell with 200.
    """
    raw_content = (lead_in.raw_content or "").strip()
    lead = db.execute(
        select(Lead).where(Lead.source == "linkedin_manual", Lead.external_id == lead_in.url)
    ).scalar_one_or_none()

    if lead is not None and (lead.description or "").strip():
        return lead

    if lead is None:
        lead = Lead(
            source="linkedin_manual",
            external_id=lead_in.url,
            title=_title_from_url(lead_in.url),
            description="",
            url=lead_in.url,
            author=lead_in.author,
            contact_email=None,
            is_manual=True,
            origin_type=lead_in.origin_type,
        )
        db.add(lead)

    if raw_content:
        _fill_from_raw_content(lead, raw_content, lead_in)
        db.commit()
        db.refresh(lead)
        return lead

    lead.origin_type = lead_in.origin_type
    db.commit()
    lead_id = lead.id
    # Release the request connection so the scrape subprocess can write to SQLite.
    db.close()

    try:
        _run_scrape_script(lead_id)
        _run_clean_script(lead_id)
        return _finalize_scraped_profile(lead_id)
    except Exception as exc:
        detail = str(exc)
        status = 503 if "login" in detail.lower() or "verification" in detail.lower() else 502
        raise HTTPException(
            status_code=status,
            detail=f"Profile scrape failed for lead {lead_id}: {detail} "
            "-- submit the same URL again to retry, or paste the profile text to skip scraping.",
        ) from exc


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


@router.put("/{lead_id}/contact-email", response_model=LeadOut)
def set_contact_email(lead_id: int, payload: LeadContactEmailIn, db: Session = Depends(get_db)) -> Lead:
    """Saves a looked-up email address on a lead, so POST /outreach/{lead_id}/email has somewhere to
    send to. Profile scraping gives context, never an address -- this is always a manual save after
    looking one up with Hunter.io or the company's own site."""
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    lead.contact_email = payload.contact_email.strip() or None
    db.commit()
    db.refresh(lead)
    lead.latest_verdict = _attach_latest_verdicts(db, [lead]).get(lead.id)  # type: ignore[attr-defined]
    lead.latest_outreach_status = _attach_latest_outreach_statuses(db, [lead]).get(lead.id)  # type: ignore[attr-defined]
    return lead
