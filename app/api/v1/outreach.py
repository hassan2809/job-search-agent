from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.lead import Lead
from app.models.match import Match
from app.models.draft_check import DraftCheck
from app.models.outreach import Outreach, OutreachMessage
from app.schemas.outreach import (
    CheckStatsOut,
    CheckStatRow,
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

# Our /connect note = the "Initial Connection" touch. Everything after that is ONE continuous
# sequence -- not a structurally different "first message" vs "follow-ups" -- each stage with its
# own purpose and minimum spacing. Manually-triggered only, never on a timer: this sets minimum
# spacing and a cap, not an automatic schedule.
#
# Spacing is 3 / 5 / 6 / 7, a 21-day span. The two research files disagree on how long this should
# take, so this splits them deliberately:
#   linkedin_outreach_strategies.txt's "Message Timing Guidelines" table sums to 29 days
#     (3-5, then 5-7, then 7-10, then 14-21) -- but the same file's conclusion says "3-4 touchpoints
#     over 2-3 weeks yield optimal results", which the table contradicts.
#   c2b_outreach_strategies.txt is tighter: first follow-up 3-5 business days, subsequent ones
#     4-7 days apart, whole sequence done inside ~15 days, and stop after 3 follow-ups.
# 21 days satisfies c2b's 4-7 day gaps, lands inside the LinkedIn file's own "2-3 weeks", and stays
# clear of the 30-day mark c2b cites for deleting contact data you never heard back from.
# Four stages = one opener plus three follow-ups, which is c2b's "2-3 follow-ups then stop".
# min_days on stage 0 only bites once /mark-reply-sent exists: before it, 'awaiting_reply' was
# reachable only via /mark-sent, which always implies message_count >= 1, so stage 0's spacing was
# never consulted. Now that replying can park you at 'awaiting_reply' with nothing staged sent yet,
# 0 here would report "follow-up due now" the moment you send a reply. 3 matches the table's
# "First Follow-up: 3-5 days after acceptance". Drafting the first message straight after
# connection_accepted is unaffected -- that path never consults this.
# The strategy doc's ladder is written for an agency selling a service (value proposition ->
# case study -> solution proposal -> soft close). I'm a developer looking for work, not a vendor,
# so the same four-step spacing is kept but each step is what a developer would actually say.
MESSAGE_STAGES = [
    {
        "purpose": "Lead with their product, mission or open role and why it genuinely interests "
        "me. Where their stack or a concrete technical problem is visible in the lead text, name it "
        "and be specific about the relief I offer rather than promising broad improvement. One "
        "sentence at most on the part of my background that connects, then an open question",
        "min_days": 3,
    },
    {
        "purpose": "PROOF POINT. Show one thing I have built that speaks to their situation. I have "
        "no enterprise case studies, so the proof is speed, a feature owned end to end, or the "
        "shape of a problem I solved: what was hard about it, how I structured it, what it does "
        "now. Where the work is client code I cannot show, describe the ARCHITECTURE rather than "
        "skipping it -- that is proof without breaching anything. It must be a DIFFERENT project "
        "from any already mentioned in the conversation above; repeating one makes a follow-up feel "
        "like a resend. Point at something they can actually check",
        "min_days": 5,
    },
    {
        "purpose": "Still anchored to their work, ask plainly whether there is a role, a contract or "
        "a project where I would fit, or who I should be talking to",
        "min_days": 6,
    },
    {
        "purpose": "SOFT CLOSE. This is the one message in the sequence that sells nothing and "
        "asks for nothing, and the SHAPE rules do not apply to it. Do NOT name a project. Do NOT "
        "describe anything I have built. Do NOT include a stack. Do NOT end with a question. "
        "Assume the timing simply isn't right, say so without a hint of grievance, and leave one "
        "concrete standing offer: if they ever hit a tight deadline or need an extra pair of hands "
        "to clear a backlog, I am around. Being someone's on-call backup developer is a smaller and "
        "more useful thing to be remembered for than being someone who wanted a job. Two or three "
        "sentences, warm and final. My portfolio link may appear once at the end, plainly, and "
        "nothing else. If it reads like a pitch, it is wrong",
        "min_days": 7,
    },
]
MAX_MESSAGE_STAGES = len(MESSAGE_STAGES)

CONNECTION_RESPONSE_STATUS_MAP = {
    "accepted": "connection_accepted",
    "declined": "connection_declined",
    "no_response": "connection_no_response",
}

# closed_not_interested covers *my* decision to stop pursuing a lead regardless of anything they
# said or didn't say -- distinct from closed_declined (they said no) and closed_no_response (they
# never replied), both of which describe the lead's behavior, not mine.
CLOSE_STATUSES = {"closed_won", "closed_declined", "closed_no_response", "closed_not_interested"}


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
    messages = list(
        db.execute(
            select(OutreachMessage).where(OutreachMessage.outreach_id == outreach_id).order_by(OutreachMessage.created_at)
        ).scalars()
    )
    # Attach whatever each draft still breaks, so the UI can flag it. One query for the thread
    # rather than one per message.
    unresolved = {
        row.message_id: row.final_failures
        for row in db.execute(
            select(DraftCheck).where(DraftCheck.outreach_id == outreach_id, DraftCheck.message_id.isnot(None))
        ).scalars()
        if row.final_failures
    }
    for message in messages:
        message.check_failures = unresolved.get(message.id, [])  # type: ignore[attr-defined]
    return messages


def _detail(outreach: Outreach, db: Session) -> OutreachDetailOut:
    return OutreachDetailOut(**OutreachOut.model_validate(outreach).model_dump(), messages=_thread(outreach.id, db))


def _record_check(
    db: Session, outreach_id: int, message_id: int, kind: str, stage_index: int | None, draft
) -> None:
    """Record what the checks found for one generated draft.

    Written for every draft, clean or not: a run with no failures is the baseline that makes the
    failure counts meaningful. Without the clean rows you can count how often a rule broke but not
    how often it held.
    """
    db.add(
        DraftCheck(
            outreach_id=outreach_id,
            message_id=message_id,
            kind=kind,
            stage_index=stage_index,
            first_failures=draft.first_failures,
            final_failures=draft.final_failures,
            retried=draft.retried,
        )
    )


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
        draft = outreach_service.draft_connection_note(lead, latest_match.fit_reasoning)
    except LLMNotConfiguredError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e

    new_outreach = Outreach(
        lead_id=lead.id, match_id=latest_match.id, origin_type=lead.origin_type, status="connection_drafted"
    )
    db.add(new_outreach)
    db.flush()
    message = OutreachMessage(outreach_id=new_outreach.id, sender="me", body=draft.body)
    db.add(message)
    db.flush()
    _record_check(db, new_outreach.id, message.id, "connection_note", None, draft)
    db.commit()
    db.refresh(new_outreach)
    return _detail(new_outreach, db)


@router.post("/{lead_id}/pass", response_model=OutreachOut)
def pass_on_lead(lead_id: int, db: Session = Depends(get_db)) -> Outreach:
    """Marks a lead as not worth pursuing, at any point -- including before fit-check/connect ever
    happen. Every other close path requires an Outreach to already exist (you can only /close an
    outreach_id), which meant there was no way to bail on a lead you'd decided against just from
    reading the profile. Creates the Outreach record here if one doesn't exist yet; reuses and
    re-closes it if one does, so this also works as a fast "never mind" from any later stage."""
    lead = _get_lead_or_404(lead_id, db)

    outreach = db.execute(
        select(Outreach).where(Outreach.lead_id == lead_id).order_by(Outreach.created_at.desc())
    ).scalars().first()

    if outreach:
        outreach.status = "closed_not_interested"
    else:
        latest_match = db.execute(
            select(Match).where(Match.lead_id == lead_id).order_by(Match.created_at.desc())
        ).scalars().first()
        outreach = Outreach(
            lead_id=lead.id,
            match_id=latest_match.id if latest_match else None,
            origin_type=lead.origin_type,
            status="closed_not_interested",
        )
        db.add(outreach)

    db.commit()
    db.refresh(outreach)
    return outreach


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
    determined by how many have already been sent.

    Allowed from 'replied' too: a reply pauses the sequence, it doesn't end it. People routinely
    accept a connection with nothing more than "nice to meet you", and someone saying "ping me next
    quarter" mid-sequence shouldn't strand the remaining stages either. The stage cap below is what
    stops this turning into nagging."""
    outreach = _get_outreach_or_404(id, db)

    if outreach.status not in ("connection_accepted", "awaiting_reply", "replied"):
        raise HTTPException(
            status_code=409,
            detail=f"Outreach is in status '{outreach.status}', expected one of 'connection_accepted', "
            "'awaiting_reply', 'replied'",
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
        draft = outreach_service.draft_next_message(
            lead,
            _thread(outreach.id, db),
            fit_reasoning,
            outreach.origin_type,
            stage_purpose,
            outreach.message_count,
            is_soft_close=outreach.message_count == MAX_MESSAGE_STAGES - 1,
        )
    except LLMNotConfiguredError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e

    message = OutreachMessage(outreach_id=outreach.id, sender="me", body=draft.body)
    db.add(message)
    db.flush()
    _record_check(db, outreach.id, message.id, "staged_message", outreach.message_count, draft)
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


@router.post("/{id}/mark-reply-sent", response_model=OutreachOut)
def mark_reply_sent(id: int, db: Session = Depends(get_db)) -> Outreach:
    """Records that I sent the suggested response that /reply drafted. Lands back on
    'awaiting_reply' -- I've said something and the ball is in their court again, exactly as it is
    after marking a staged message sent. Without this a thread sticks in 'replied' forever and the
    UI keeps telling you to review a suggestion you already sent."""
    outreach = _get_outreach_or_404(id, db)
    _require_status(outreach, "replied")
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
        draft = outreach_service.suggest_reply(lead, _thread(outreach.id, db))
    except LLMNotConfiguredError as e:
        db.commit()
        raise HTTPException(status_code=503, detail=str(e)) from e

    message = OutreachMessage(outreach_id=outreach.id, sender="me", body=draft.body)
    db.add(message)
    db.flush()
    _record_check(db, outreach.id, message.id, "reply_suggestion", None, draft)
    db.commit()
    db.refresh(outreach)
    return _detail(outreach, db)


@router.post("/{id}/close", response_model=OutreachOut)
def close(id: int, close_in: CloseIn, db: Session = Depends(get_db)) -> Outreach:
    if close_in.status not in CLOSE_STATUSES:
        raise HTTPException(status_code=400, detail=f"status must be one of: {', '.join(sorted(CLOSE_STATUSES))}")

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


@router.get("/check-stats", response_model=CheckStatsOut)
def check_stats(db: Session = Depends(get_db)) -> CheckStatsOut:
    """How often the deterministic checks fire, and whether the retry fixes them.

    This is the question the checks exist to answer: which prompt rules keep leaking. `first_attempt`
    counts every time a rule broke on the first draft -- including the ones the retry then fixed,
    which is why the failures are recorded per attempt rather than only on the stored message.
    A rule with a high first_attempt count is a prompt that isn't landing; a high `unresolved`
    count means the retry can't fix it either and the rule needs a different approach.
    """
    rows = list(db.execute(select(DraftCheck)).scalars())
    first_counts: dict[str, int] = {}
    unresolved_counts: dict[str, int] = {}
    for row in rows:
        for failure in row.first_failures or []:
            code = failure.get("code", "unknown")
            first_counts[code] = first_counts.get(code, 0) + 1
        for failure in row.final_failures or []:
            code = failure.get("code", "unknown")
            unresolved_counts[code] = unresolved_counts.get(code, 0) + 1

    by_rule = [
        CheckStatRow(code=code, first_attempt=count, unresolved=unresolved_counts.get(code, 0))
        for code, count in sorted(first_counts.items(), key=lambda kv: -kv[1])
    ]
    return CheckStatsOut(
        drafts=len(rows),
        clean_first_time=sum(1 for r in rows if not r.first_failures),
        retried=sum(1 for r in rows if r.retried),
        retry_fixed_all=sum(1 for r in rows if r.retried and not r.final_failures),
        still_broken=sum(1 for r in rows if r.final_failures),
        by_rule=by_rule,
    )


@router.get("/{id}", response_model=OutreachDetailOut)
def get_outreach(id: int, db: Session = Depends(get_db)) -> OutreachDetailOut:
    outreach = _get_outreach_or_404(id, db)
    return _detail(outreach, db)
