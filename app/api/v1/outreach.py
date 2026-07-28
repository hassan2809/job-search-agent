from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.lead import Lead
from app.models.match import Match
from app.models.outreach import Outreach, OutreachMessage
from app.schemas.outreach import (
    CloseIn,
    ConnectionResponseIn,
    MatchOut,
    NeedsNextMessageOut,
    OutreachDetailOut,
    OutreachOut,
    ReplyIn,
)
from app.services import outreach as outreach_service
from app.services.llm.client import LLMNotConfiguredError

router = APIRouter()

# From linkedin_outreach_strategies.txt's "Message Timing Guidelines" table. Our /connect
# note = their "Initial Connection". Everything after that is ONE continuous sequence --
# not a structurally different "first message" vs "follow-ups" -- each stage with its own
# purpose and minimum spacing:
#   First Follow-up:  3-5 days after acceptance -- value proposition (min_days: 0, you decide
#                      when to send the first one, no minimum enforced)
#   Second Follow-up: 5-7 days later   -- share a relevant case study
#   Third Follow-up:  7-10 days later  -- specific solution proposal
#   Final Message:    14-21 days after third -- soft close or alternative offer
# Manually-triggered only, never on a timer -- this table sets minimum spacing and a cap,
# not an automatic schedule.
MESSAGE_STAGES = [
    {"purpose": "Value proposition -- state clearly and specifically how I can help", "min_days": 0},
    {"purpose": "Share a relevant case study or concrete proof point", "min_days": 5},
    {"purpose": "Propose a specific next step or solution", "min_days": 7},
    {"purpose": "Soft close -- a graceful final message offering a lower-commitment alternative, or a clean way to end the thread", "min_days": 14},
]
MAX_MESSAGE_STAGES = len(MESSAGE_STAGES)

CONNECTION_RESPONSE_STATUS_MAP = {
    "accepted": "connection_accepted",
    "declined": "connection_declined",
    "no_response": "connection_no_response",
}


def _get_lead_or_404(lead_id: int, db: Session) -> Lead:
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


def _get_outreach_or_404(outreach_id: int, db: Session) -> Outreach:
    outreach = db.get(Outreach, outreach_id)
    if not outreach:
        raise HTTPException(status_code=404, detail="Outreach not found")
    return outreach


def _require_status(outreach: Outreach, expected: str) -> None:
    if outreach.status != expected:
        raise HTTPException(
            status_code=409, detail=f"Outreach is in status '{outreach.status}', expected '{expected}' for this action"
        )


def _thread(outreach_id: int, db: Session) -> list[OutreachMessage]:
    return list(
        db.execute(
            select(OutreachMessage).where(OutreachMessage.outreach_id == outreach_id).order_by(OutreachMessage.created_at)
        ).scalars()
    )


def _detail(outreach: Outreach, db: Session) -> OutreachDetailOut:
    return OutreachDetailOut(**OutreachOut.model_validate(outreach).model_dump(), messages=_thread(outreach.id, db))


@router.post("/{lead_id}/fit-check", response_model=MatchOut)
def fit_check(lead_id: int, force: bool = False, db: Session = Depends(get_db)) -> Match:
    """Idempotent by default -- if a fit-check already ran for this lead, returns it instead of
    spending another LLM call. Pass force=true to deliberately re-run it (e.g. after the lead's
    description changed)."""
    lead = _get_lead_or_404(lead_id, db)

    if not force:
        existing = db.execute(
            select(Match).where(Match.lead_id == lead.id).order_by(Match.created_at.desc())
        ).scalars().first()
        if existing:
            return existing

    try:
        verdict, reasoning = outreach_service.run_fit_check(lead)
    except LLMNotConfiguredError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e

    match = Match(lead_id=lead.id, fit_verdict=verdict, fit_reasoning=reasoning)
    db.add(match)
    db.commit()
    db.refresh(match)
    return match


@router.post("/{lead_id}/connect", response_model=OutreachDetailOut)
def connect(lead_id: int, force: bool = False, db: Session = Depends(get_db)) -> OutreachDetailOut:
    """Idempotent by default -- if a connection note was already drafted for this lead, returns
    it instead of spending another LLM call. Pass force=true to deliberately draft another one."""
    lead = _get_lead_or_404(lead_id, db)

    if not force:
        existing = db.execute(
            select(Outreach).where(Outreach.lead_id == lead.id).order_by(Outreach.created_at.desc())
        ).scalars().first()
        if existing:
            return _detail(existing, db)

    latest_match = db.execute(
        select(Match).where(Match.lead_id == lead.id).order_by(Match.created_at.desc())
    ).scalars().first()
    if not latest_match:
        raise HTTPException(status_code=409, detail="Run /fit-check before requesting a connection")
    if latest_match.fit_verdict == "not_a_fit":
        raise HTTPException(status_code=409, detail="Fit-check verdict is 'not_a_fit' -- not sending a connection request")

    try:
        note = outreach_service.draft_connection_note(lead, latest_match.fit_reasoning)
    except LLMNotConfiguredError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e

    new_outreach = Outreach(
        lead_id=lead.id, match_id=latest_match.id, origin_type=lead.origin_type, status="connection_drafted"
    )
    db.add(new_outreach)
    db.flush()
    db.add(OutreachMessage(outreach_id=new_outreach.id, sender="me", body=note))
    db.commit()
    db.refresh(new_outreach)
    return _detail(new_outreach, db)


@router.get("/by-lead/{lead_id}", response_model=OutreachDetailOut)
def get_outreach_by_lead(lead_id: int, db: Session = Depends(get_db)) -> OutreachDetailOut:
    """Lets the lead detail page look up its outreach state (if any) without already knowing the
    outreach id -- /connect returns the id once created, but a page reload only has the lead id."""
    outreach = db.execute(
        select(Outreach).where(Outreach.lead_id == lead_id).order_by(Outreach.created_at.desc())
    ).scalars().first()
    if not outreach:
        raise HTTPException(status_code=404, detail="No outreach yet for this lead")
    return _detail(outreach, db)


@router.post("/{id}/mark-connection-sent", response_model=OutreachOut)
def mark_connection_sent(id: int, db: Session = Depends(get_db)) -> Outreach:
    outreach = _get_outreach_or_404(id, db)
    _require_status(outreach, "connection_drafted")
    outreach.status = "connection_sent"
    db.commit()
    db.refresh(outreach)
    return outreach


@router.post("/{id}/connection-response", response_model=OutreachOut)
def connection_response(id: int, response_in: ConnectionResponseIn, db: Session = Depends(get_db)) -> Outreach:
    outreach = _get_outreach_or_404(id, db)
    _require_status(outreach, "connection_sent")

    new_status = CONNECTION_RESPONSE_STATUS_MAP.get(response_in.status)
    if not new_status:
        raise HTTPException(status_code=400, detail="status must be one of: accepted, declined, no_response")

    outreach.status = new_status
    db.commit()
    db.refresh(outreach)
    return outreach


@router.post("/{id}/next-message", response_model=OutreachDetailOut)
def next_message(id: int, db: Session = Depends(get_db)) -> OutreachDetailOut:
    """Drafts the next message in the sequence -- the first real pitch (right after connection
    acceptance) and every follow-up alike, since they're one continuous sequence, not separate
    actions. Which stage (value proposition / case study / solution proposal / soft close) is
    determined by how many have already been sent."""
    outreach = _get_outreach_or_404(id, db)

    if outreach.status not in ("connection_accepted", "awaiting_reply"):
        raise HTTPException(
            status_code=409,
            detail=f"Outreach is in status '{outreach.status}', expected 'connection_accepted' or 'awaiting_reply'",
        )
    if outreach.message_count >= MAX_MESSAGE_STAGES:
        raise HTTPException(
            status_code=409,
            detail=f"Already sent all {MAX_MESSAGE_STAGES} stage messages with no reply -- close this as "
            "closed_no_response instead of sending another.",
        )

    lead = _get_lead_or_404(outreach.lead_id, db)
    match = db.get(Match, outreach.match_id) if outreach.match_id else None
    fit_reasoning = match.fit_reasoning if match else ""
    stage_purpose = MESSAGE_STAGES[outreach.message_count]["purpose"]

    try:
        message_body = outreach_service.draft_next_message(
            lead, _thread(outreach.id, db), fit_reasoning, outreach.origin_type, stage_purpose
        )
    except LLMNotConfiguredError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e

    db.add(OutreachMessage(outreach_id=outreach.id, sender="me", body=message_body))
    outreach.message_count += 1
    outreach.status = "message_drafted"
    db.commit()
    db.refresh(outreach)
    return _detail(outreach, db)


@router.post("/{id}/mark-sent", response_model=OutreachOut)
def mark_sent(id: int, db: Session = Depends(get_db)) -> Outreach:
    outreach = _get_outreach_or_404(id, db)
    _require_status(outreach, "message_drafted")
    outreach.status = "awaiting_reply"
    db.commit()
    db.refresh(outreach)
    return outreach


@router.post("/{id}/reply", response_model=OutreachDetailOut)
def reply(id: int, reply_in: ReplyIn, db: Session = Depends(get_db)) -> OutreachDetailOut:
    outreach = _get_outreach_or_404(id, db)
    lead = _get_lead_or_404(outreach.lead_id, db)

    db.add(OutreachMessage(outreach_id=outreach.id, sender="them", body=reply_in.body))
    outreach.status = "replied"
    db.flush()

    try:
        suggestion = outreach_service.suggest_reply(lead, _thread(outreach.id, db))
    except LLMNotConfiguredError as e:
        db.commit()
        raise HTTPException(status_code=503, detail=str(e)) from e

    db.add(OutreachMessage(outreach_id=outreach.id, sender="me", body=suggestion))
    db.commit()
    db.refresh(outreach)
    return _detail(outreach, db)


@router.post("/{id}/close", response_model=OutreachOut)
def close(id: int, close_in: CloseIn, db: Session = Depends(get_db)) -> Outreach:
    outreach = _get_outreach_or_404(id, db)
    outreach.status = close_in.status
    db.commit()
    db.refresh(outreach)
    return outreach


@router.get("/needs-next-message", response_model=list[NeedsNextMessageOut])
def needs_next_message(min_days_override: int | None = None, db: Session = Depends(get_db)) -> list[NeedsNextMessageOut]:
    """Surfaces outreaches that have been waiting long enough to be worth nudging.

    Uses the graduated MESSAGE_STAGES spacing by default (5 / 7 / 14 days, matching
    linkedin_outreach_strategies.txt) -- pass min_days_override to use a flat threshold instead.
    This only reports what's due -- it never sends anything. You still call
    POST /{id}/next-message yourself for whichever of these you want to act on.
    """
    candidates = list(
        db.execute(
            select(Outreach).where(Outreach.status == "awaiting_reply", Outreach.message_count < MAX_MESSAGE_STAGES)
        ).scalars()
    )

    due = []
    now = datetime.now(timezone.utc)
    for outreach in candidates:
        last_message = db.execute(
            select(OutreachMessage)
            .where(OutreachMessage.outreach_id == outreach.id)
            .order_by(OutreachMessage.created_at.desc())
        ).scalars().first()
        if not last_message:
            continue

        required_gap = (
            min_days_override if min_days_override is not None else MESSAGE_STAGES[outreach.message_count]["min_days"]
        )
        last_sent_at = last_message.created_at.replace(tzinfo=timezone.utc)
        days_waiting = (now - last_sent_at).days
        if days_waiting < required_gap:
            continue

        lead = db.get(Lead, outreach.lead_id)
        due.append(
            NeedsNextMessageOut(
                **OutreachOut.model_validate(outreach).model_dump(),
                lead_title=lead.title if lead else "",
                days_since_last_message=days_waiting,
            )
        )

    return due


@router.get("/{id}", response_model=OutreachDetailOut)
def get_outreach(id: int, db: Session = Depends(get_db)) -> OutreachDetailOut:
    outreach = _get_outreach_or_404(id, db)
    return _detail(outreach, db)
