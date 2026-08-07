"""Episodes: one past outreach, reconstructed from what already happened.

Deliberately a read-model over `outreaches`, `outreach_messages`, `matches` and `draft_checks`
rather than a new table. Everything here is derivable, and a stored copy would only be a second
version of the truth that drifts the moment a message is revised or an outcome is corrected.

An episode is the unit a reflection learns from: this kind of lead, approached this way, ended
like this. That is only useful once the outcome is known, which is why `outcome` separates what
THEY did (replied, declined, went quiet) from what I did (dropped it), and treats the latter as
carrying no signal about the message.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.draft_check import DraftCheck
from app.models.lead import Lead
from app.models.match import Match
from app.models.outreach import Outreach, OutreachMessage

# Outcomes that say something about whether the approach worked.
LEARNABLE_OUTCOMES = {
    "won",
    "replied",
    "declined",
    "accepted_no_reply",
    "connection_declined",
    "connection_ignored",
}

CONNECTION_SENT_STATUSES = {
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
}

HOOK_WORDS = 14


@dataclass
class Episode:
    outreach_id: int
    lead_id: int
    lead_author: str
    lead_type: str | None
    fit_verdict: str | None
    origin_type: str
    status: str
    outcome: str
    connection_accepted: bool | None
    stages_sent: int
    got_reply: bool
    days_to_first_reply: int | None
    hook: str
    projects_mentioned: list[str] = field(default_factory=list)
    unresolved_failures: int = 0
    # Index this episode is filed under; see intent_key().
    intent: str = ""


def _outcome(status: str, got_reply: bool) -> str:
    """Bucket the status into something a reflection can learn from.

    `dropped` is my own decision to stop pursuing a lead and says nothing about whether the message
    worked, so it is excluded from LEARNABLE_OUTCOMES. Counting it as a failure would teach the
    wrong lesson, since the message may never have been sent at all.
    """
    if status == "closed_won":
        return "won"
    if status == "closed_not_interested":
        return "dropped"
    if status == "connection_declined":
        return "connection_declined"
    if status == "connection_no_response":
        return "connection_ignored"
    # An explicit no is engagement, and a different lesson from silence: the message reached them
    # and they answered it. Keep the two apart or a reflection will treat both as "did not work".
    if status == "closed_declined":
        return "declined"
    if status == "closed_no_response":
        return "accepted_no_reply"
    if got_reply:
        return "replied"
    return "open"


def _days_between(earlier: datetime, later: datetime) -> int:
    # Columns are naive UTC (see app/models/outreach.py), so compare them as such.
    return max((later - earlier).days, 0)


def build_episodes(db: Session, *, project_names: tuple[str, ...] = ()) -> list[Episode]:
    outreaches = list(db.execute(select(Outreach).order_by(Outreach.created_at)).scalars())
    if not outreaches:
        return []

    ids = [o.id for o in outreaches]
    messages: dict[int, list[OutreachMessage]] = {i: [] for i in ids}
    for message in db.execute(
        select(OutreachMessage).where(OutreachMessage.outreach_id.in_(ids)).order_by(OutreachMessage.created_at)
    ).scalars():
        messages.setdefault(message.outreach_id, []).append(message)

    matches = {m.id: m for m in db.execute(select(Match)).scalars()}
    leads = {lead.id: lead for lead in db.execute(select(Lead).where(Lead.id.in_([o.lead_id for o in outreaches]))).scalars()}

    unresolved: dict[int, int] = {}
    # Which messages were staged sequence messages rather than replies. Position alone cannot tell
    # them apart: when a lead answers the connection note, the second message of mine is a reply
    # draft, not an opening, and reading it as the hook mislabels the one field retrieval shows.
    kinds: dict[int, str] = {}
    for row in db.execute(select(DraftCheck).where(DraftCheck.outreach_id.in_(ids))).scalars():
        if row.final_failures:
            unresolved[row.outreach_id] = unresolved.get(row.outreach_id, 0) + len(row.final_failures)
        if row.message_id:
            kinds[row.message_id] = row.kind

    episodes: list[Episode] = []
    for outreach in outreaches:
        thread = messages.get(outreach.id, [])
        mine = [m for m in thread if m.sender == "me"]
        theirs = [m for m in thread if m.sender == "them"]
        match = matches.get(outreach.match_id) if outreach.match_id else None
        lead = leads.get(outreach.lead_id)

        # Prefer what draft_checks recorded; fall back to position for anything drafted before the
        # checks existed, and only then when a staged message is known to have been sent at all.
        tagged = [m for m in mine if kinds.get(m.id) == "staged_message"]
        if tagged:
            staged = tagged
        elif outreach.message_count > 0 and any(m.id in kinds for m in mine):
            staged = []  # kinds are known for this thread and none is staged: there is no hook
        else:
            staged = mine[1:] if outreach.message_count > 0 else []
        hook = " ".join(staged[0].body.split()[:HOOK_WORDS]) if staged else ""

        days_to_reply = None
        if theirs and mine:
            days_to_reply = _days_between(mine[0].created_at, theirs[0].created_at)

        accepted: bool | None = None
        if outreach.status in {"connection_declined", "connection_no_response"}:
            accepted = False
        elif outreach.status in CONNECTION_SENT_STATUSES - {"connection_sent"}:
            accepted = True

        body_all = " ".join(m.body.lower() for m in mine)
        episodes.append(
            Episode(
                outreach_id=outreach.id,
                lead_id=outreach.lead_id,
                lead_author=lead.author if lead else "",
                lead_type=match.lead_type if match else None,
                fit_verdict=match.fit_verdict if match else None,
                origin_type=outreach.origin_type,
                status=outreach.status,
                outcome=_outcome(outreach.status, bool(theirs)),
                connection_accepted=accepted,
                stages_sent=outreach.message_count,
                got_reply=bool(theirs),
                days_to_first_reply=days_to_reply,
                hook=hook,
                projects_mentioned=[p for p in project_names if p.lower() in body_all],
                unresolved_failures=unresolved.get(outreach.id, 0),
                intent=intent_key(match.lead_type if match else None, outreach.origin_type),
            )
        )
    return episodes


def summarise(episodes: list[Episode]) -> dict:
    """Counts a reflection (or a human) can read without re-deriving them.

    Rates are computed over episodes with a KNOWN outcome only. Including in-flight ones would
    dilute every rate toward zero and make early results look worse the more outreach is running.
    """
    known = [e for e in episodes if e.outcome in LEARNABLE_OUTCOMES]
    by_type: dict[str, dict[str, int]] = {}
    for episode in known:
        bucket = by_type.setdefault(episode.lead_type or "unknown", {"episodes": 0, "replied": 0})
        bucket["episodes"] += 1
        if episode.got_reply:
            bucket["replied"] += 1

    return {
        "total": len(episodes),
        "with_known_outcome": len(known),
        "open": sum(1 for e in episodes if e.outcome == "open"),
        "dropped_by_me": sum(1 for e in episodes if e.outcome == "dropped"),
        "replied": sum(1 for e in known if e.got_reply),
        "by_lead_type": by_type,
        "by_outcome": {
            outcome: sum(1 for e in episodes if e.outcome == outcome)
            for outcome in sorted({e.outcome for e in episodes})
        },
    }


# A reflection over a handful of episodes invents patterns from noise, and because the result is
# injected into every draft, a wrong lesson gets applied everywhere. Hold the line until there is
# enough to say something true.
MIN_EPISODES_FOR_REFLECTION = 30


def episodes_as_text(episodes: list[Episode]) -> str:
    """One line per closed episode, for the reflection prompt. Open episodes are excluded: they
    have no outcome yet, so they carry no lesson."""
    lines = []
    for e in episodes:
        if e.outcome not in LEARNABLE_OUTCOMES:
            continue
        projects = ", ".join(e.projects_mentioned) or "none"
        reply = f"replied in {e.days_to_first_reply}d" if e.got_reply else "no reply"
        lines.append(
            f"- type={e.lead_type or 'unknown'} | fit={e.fit_verdict or 'unknown'} | "
            f"origin={e.origin_type} | stages_sent={e.stages_sent} | projects={projects} | "
            f"{reply} | outcome={e.outcome} | opened: \"{e.hook}\""
        )
    return "\n".join(lines)


def intent_key(lead_type: str | None, origin_type: str) -> str:
    """The index an episode is filed under, and the key a new draft looks up.

    The AgentCore strategy indexes episodes on "intent" -- what the message was trying to do and
    for whom. Here that is the kind of lead plus how they were found, because those two decide what
    the message has to achieve. Two outreaches to consultants found cold are the same problem;
    the same words sent to a hiring engineering team are a different one.
    """
    return f"{lead_type or 'unknown'}/{origin_type}"


def retrieve_similar(
    episodes: list[Episode], *, lead_type: str | None, origin_type: str, limit: int = 3
) -> list[Episode]:
    """Past outreach worth looking at before writing this one.

    Only episodes with a known outcome: an open one teaches nothing, and padding the list with
    them would make thin evidence look substantial. Exact intent matches come first, then anything
    sharing the lead type, so a new consultant lead can still learn from consultants found a
    different way. Replies are ordered first because a message that worked is the more useful
    example, but failures are deliberately kept in the list -- knowing which opening was ignored is
    half the value.
    """
    known = [e for e in episodes if e.outcome in LEARNABLE_OUTCOMES]
    if not known:
        return []

    wanted = intent_key(lead_type, origin_type)
    exact = [e for e in known if e.intent == wanted]
    same_type = [e for e in known if e.intent != wanted and e.lead_type and e.lead_type == lead_type]

    ordered = sorted(exact, key=lambda e: not e.got_reply) + sorted(same_type, key=lambda e: not e.got_reply)
    return ordered[:limit]


def as_recall_text(episodes: list[Episode]) -> str:
    """Render retrieved episodes for a drafting prompt.

    Linearized deliberately: the opening line and what happened, not the whole record. The strategy
    doc's advice is to feed only the main steps so the model focuses on them, and a full dump of
    every field would bury the one thing that matters -- whether this approach got an answer.

    Returns an explicit "none" rather than an empty string, so the prompt never silently loses a
    section and the model is told the difference between "no history" and "history withheld".
    """
    if not episodes:
        return "No comparable past outreach with a known outcome yet. Ignore this section."

    lines = []
    for e in episodes:
        result = f"replied in {e.days_to_first_reply}d" if e.got_reply else f"no reply ({e.outcome})"
        # An episode where they answered the connection note carries a real lesson even though no
        # staged message was ever sent, so say that rather than printing an empty opening.
        opening = f'opened: "{e.hook}"' if e.hook else "no staged message sent, they replied to the connection note"
        lines.append(f"- {e.intent} | {e.stages_sent} message(s) | {result} | {opening}")

    caveat = (
        "These are only a handful of examples, so treat them as anecdote rather than evidence."
        if len(episodes) < 3
        else "Still a small sample. Use it as a hint, not a rule."
    )
    return "\n".join(lines) + f"\n{caveat}"
