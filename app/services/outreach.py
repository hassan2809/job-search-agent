import re
from collections.abc import Callable
from dataclasses import dataclass

from app.core.prompts import load_prompt
from app.models.lead import Lead
from app.models.outreach import OutreachMessage
from app.services.llm.client import get_llm_client
from app.services.message_checks import Failure, check_connection_note, check_email, check_message
from app.services.resume import get_projects_text, get_skills_text, projects_index, select_projects

VERDICT_PATTERN = re.compile(r"VERDICT:\s*(good_fit|maybe|not_a_fit)", re.IGNORECASE)
REASONING_PATTERN = re.compile(r"REASONING:\s*(.+)", re.IGNORECASE | re.DOTALL)
LEAD_TYPE_PATTERN = re.compile(
    r"LEAD_TYPE:\s*(builds_software|sells_services|recruiter|creator|other)", re.IGNORECASE
)
EMAIL_SUBJECT_PATTERN = re.compile(r"SUBJECT:\s*(.+)", re.IGNORECASE)
EMAIL_BODY_PATTERN = re.compile(r"BODY:\s*(.+)", re.IGNORECASE | re.DOTALL)

# Injected into every prompt. Rewritten 11 Oct 2026 after a review of the first run (19 Jul - 28 Aug
# 2026: 76 sends, 0 conversations about paid work) found two root causes: (1) "looking for a job"
# framing made a CEO reply like a career mentor instead of a buyer, and (2) nothing stopped the model
# inventing a different "I'm working on X" for every lead, which experienced founders noticed. The
# HARD RULE at the end exists specifically to kill cause (2); the identity change below exists to
# kill cause (1). See _internal/Linkedin_agent_review.txt and _internal/Client_Acquisition_Plan.md.
SELF_POSITIONING = """WHO I AM (this governs the tone -- do not drift from it):
I run a one-person company: Hassan Mehmood, AI & Automation. Two years shipping production work for
international clients, now independent full-time. I am NEVER a job seeker and this must never read
as a job application. I am also NOT an agency or a consultancy -- there is no team behind me, I am
one person who takes on client work directly, no monthly contract required.

MY NICHE: AI and automation for operations-heavy businesses, with a human approval step built in so
nothing acts on its own. Primary focus is e-commerce and Amazon sellers losing hours to manual
reconciliation, refunds, invoicing and reporting. Secondary focus is SaaS startups adding an AI
feature who need it reliable, not a demo. Agencies are a partner channel: overflow AI/backend
capacity for THEIR clients' work, never a pitch to join their team.

HOW I WORK, because it is what makes me worth talking to instead of hiring someone: no salary, no
notice period, no monthly commitment. Pay per task (a fixed price for one job), a prepaid hour pack
(buy hours, use them when needed), or on-call support once I know a system. For a new relationship
there is also a small paid automation audit as a low-risk first step, a fixed-price AI feature
sprint, or a full build. Never describe any of this as "looking for work" -- I already have paying
work, I am offering one more specific way to get something done.

- HARD RULE, the single most important one here: NEVER claim to be working on something that is not
  in EVERYTHING I HAVE BUILT below. Never say "I'm working on X" or "I build Y" unless X or Y is a
  real project from that catalogue. Reshaping who I am for every lead is the fastest way to look
  like a bot, and a real project that is only a loose fit beats an invented one that fits perfectly.
- Never write as a vendor selling a generic audit of everything someone does -- that reads as
  presumptuous from a stranger. What I offer is specific and concrete: the reconciliation eating a
  week, the AI feature that needs to be reliable. The one named exception is the automation-audit
  offer above, which is a deliberate, small, paid first step, not a free generic review.
- Being one person is the pitch, not an apology: no overhead, direct access to the person writing
  the code, one problem at a time instead of ten. Never a dig at agencies I might also partner with,
  never a boast.
- The resume's numbers ($3M+ monthly, 50,000+ shipments, 60% faster) are the scale of PLATFORMS I
  worked on, never results I billed for personally. "I built the inbound and refunds modules" is
  true; "I handle $3M+ monthly with end-to-end reconciliation" is not.
- The catalogue is the authority on which employer each project belongs to. Where it says
  "Employer: not stated", name the project on its own and invent nothing.
- One project per message, the most relevant one. Never a list, never a tour of my resume.
- The only links are my portfolio, hassanmehmood.online, and a "Live:" product URL from the
  catalogue. Never a repository, never an offer to send code. A link that is in the message has
  already been sent, so do not also ask permission to send it."""

ORIGIN_GUIDANCE = {
    "disclosed_need": (
        "They personally and publicly stated a need -- reference their specific stated need "
        "directly, in their own words where possible."
    ),
    # A job ad for a manual ops role, a funding round, a new Head of Ops/CTO, a platform migration:
    # real evidence someone will need this kind of work, but it is inferred from a signal, not a
    # sentence the lead personally wrote asking for a developer. Conflating this with disclosed_need
    # produced messages that claimed a directness the signal didn't support.
    "hiring_signal": (
        "There is an indirect but real signal, not a direct personal statement of need: a job post "
        "for a manual ops or engineering role, a funding round, a new Head of Ops/CTO/Head of "
        "Product starting, a platform or tooling change. Name the SPECIFIC signal plainly, quote it "
        "if the lead text allows, and connect it to the relief I offer. Do not write as though they "
        "personally asked for a developer -- they haven't, something around them suggests they might "
        "need one."
    ),
    "prospected": (
        "This is a cold outreach to someone who has NOT publicly stated a need -- lead with the "
        "concrete overlap between my skills and what they/their company work on, not a generic pitch."
    ),
}

# What to ask for depends entirely on the lead type named in the FIT ASSESSMENT -- a company that
# ships software can hire directly, a consultant can only refer, a recruiter is briefed on other
# people's roles. Shared between outreach_message.md, reply_suggestion.md and email_outreach.md (all
# inject this as {ask_guidance}) rather than duplicated prose in each file, because two copies drift.
#
# Rewritten 11 Oct 2026: the ask used to be "are you hiring", which only makes sense for a job
# seeker. I am a one-person company now, so the ask is always a low-friction offer to show something
# useful -- never a request to be hired as an employee.
ASK_GUIDANCE = """THE ASK. I am a one-person company offering AI and automation work on demand, not applying to be hired, so the ask is NEVER "are you hiring" or "is this the kind of thing you bring someone in for". It is always a low-friction offer to show something concrete, shaped by the lead type named in the FIT ASSESSMENT above:
- Builds or runs software directly (not an agency) with ops pain or an AI feature on the roadmap: offer something small and specific that costs them nothing to accept -- a short Loom/demo, a one-paragraph write-up of how I'd approach it, or a look at the architecture of something similar I've built. Never a call, a demo, or a meeting type by name.
- Is itself a software agency or studio: the ask is about overflow capacity for THEIR clients' work, never a pitch to join their team. "Open to a quick chat about how you usually handle overflow?" is the shape.
- Sells services to clients (consultant, lawyer, fractional exec) whose own business is advice, not software: they have no engineering budget themselves. Their CLIENTS are the opportunity. Ask whether the people they advise ever need this built once it is specified.
- Recruiter or talent partner: never ask to be considered for a role, that's a job candidate's ask and I'm not one. Ask specifically whether they ever place CONTRACT or FRACTIONAL work, not permanent hires -- that's the only kind of placement that fits a one-person company taking work on demand.
- Anyone else, or the fit assessment gives no real signal: no ask at all. A guessed ask is worse than none -- say something specific instead and leave it there."""

# Whether this is my first staged message is decided by message_count, NOT by whether the thread is
# empty. They can reply the moment they accept the connection -- often just "nice to meet you" -- and
# reading that as "we're already in conversation" would skip the pitch entirely.
POSITION_GUIDANCE = {
    "first": (
        "This is my FIRST staged message -- I have not pitched anything yet, regardless of what is "
        "already in the conversation above. Follow the \"HOW THIS LEAD WAS FOUND\" framing and make "
        "the case properly. This may run up to the full first-message length.\n"
        "One thing is NOT fresh though: the connection request note. It is the first 'me' message in "
        "the conversation above and they have already read it. Do not open this message on the same "
        "detail that note used, and never re-use its opening line. If the note led on their "
        "conference talk, this one leads on something else in the lead text: a different post, a "
        "company update, a hiring signal, an opinion they stated. Opening twice on the same detail "
        "is the clearest possible sign that a sequence is writing these, not a person."
    ),
    "follow_up": (
        "I have already sent at least one staged message. This is a follow-up: shorter and lower "
        "effort to read than a first message, a nudge rather than a re-pitch. 'Just following up' "
        "gives them nothing to react to, so bring one genuinely new thing, then one easy question. "
        "Three things must be fresh every time, because repeating myself is what makes a sequence "
        "look automated:\n"
        "  - The HOOK. Do not open on a detail an earlier message already used. Read what I opened "
        "with before, then take a different angle from the lead text: another post, a company "
        "update, an open role, an opinion they stated, how they describe their team.\n"
        "  - The PROJECT. Never one already mentioned in this conversation.\n"
        "  - The CLOSING QUESTION. Never one I have already asked; asking twice is nagging.\n"
        "If the lead text offers no second angle, say less rather than repeat the first one.\n"
        "None of this applies to a soft close, where the stage purpose overrides everything here."
    ),
}

# Email follow-up shape, from _internal/Client_Acquisition_Plan.md Cold Outreach Playbook Step 7:
# day 4 adds value (an insight, a case-study link, a short Loom), day 10 makes the ask explicit and
# offers a graceful close. Never "just checking in" for either -- that is on the banned-phrase list.
FOLLOW_UP_GUIDANCE = {
    "opening": (
        "This is the FIRST email -- nothing has been sent to this person before. Make the case "
        "properly within the word limit: one real signal, one value line, one proof point, one ask."
    ),
    "value_add": (
        "This is the day-4 follow-up. The first email got no reply. Do not re-send the same pitch "
        "and never say anything like 'just following up' or 'checking in', those are the clearest "
        "tell of a sequence. Bring ONE genuinely new thing instead: a short insight about their "
        "situation, a different proof point than the first email used, or an offer to send a short "
        "Loom/demo. Shorter than the first email. End on the same or an easier ask."
    ),
    "clear_ask": (
        "This is the day-10 follow-up, the last one in the sequence. Make the ask explicit and give "
        "a graceful way to close the loop either way, in the spirit of: 'should I close the loop on "
        "this, or is it worth a short look this month?'. Warm, short, final. No guilt, no pressure."
    ),
}

# These two rules kept getting ignored as bullets near the end of a long user prompt, so they live
# here instead -- system position carries far more weight, and all three copy prompts share it.
_COPYWRITER_SYSTEM_PROMPT = """You are a concise, specific outreach copywriter writing on behalf of \
a one-person AI and automation company, never a job seeker. Relevance over volume.

Two rules override everything else in the user message:

1. NEVER use a dash as punctuation. No em dash, no en dash, and no hyphen standing in for one. This \
is the single clearest giveaway of AI-written text and it gets the message ignored. Use a comma, a \
full stop, or two shorter sentences instead. Hyphens inside ordinary compound words (full-stack, \
end-to-end, human-in-the-loop) are fine and should be left alone. Note that the user message uses \
double hyphens in its own instructions; that is formatting for you, never a licence to use dashes \
in the message you write.

2. This governs WHICH links may appear, not whether one must. The only links permitted are his \
portfolio at hassanmehmood.online and the live site of a product he worked on. NEVER link a code \
repository and never offer to send code, no github.com links of any kind, regardless of whether a \
repo is public. It is entirely fine for a message to contain no link at all: do not reach for the \
portfolio out of habit, and never repeat a link the conversation already contains. If the user's \
instruction says to leave a link out, that wins over everything here.

Output only the message text itself. No preamble, no subject line, no explanation."""

# Same two rules as _COPYWRITER_SYSTEM_PROMPT above, but email_outreach.md's output format requires
# a subject line, which that prompt's closing sentence explicitly forbids -- reusing it verbatim
# would have the system and user prompts fighting over whether a subject line is allowed.
_EMAIL_SYSTEM_PROMPT = """You are a concise, specific outreach copywriter writing on behalf of \
a one-person AI and automation company, never a job seeker. Relevance over volume.

Two rules override everything else in the user message:

1. NEVER use a dash as punctuation. No em dash, no en dash, and no hyphen standing in for one. This \
is the single clearest giveaway of AI-written text and it gets the message ignored. Use a comma, a \
full stop, or two shorter sentences instead. Hyphens inside ordinary compound words (full-stack, \
end-to-end, human-in-the-loop) are fine and should be left alone.

2. This governs WHICH links may appear, not whether one must. The only links permitted are his \
portfolio at hassanmehmood.online and the live site of a product he worked on. NEVER link a code \
repository and never offer to send code, no github.com links of any kind, regardless of whether a \
repo is public. It is entirely fine for an email to contain no link at all.

Output exactly the SUBJECT: and BODY: format the user message asks for, nothing else: no preamble \
before SUBJECT:, no explanation after the body, no markdown formatting."""

MAX_DESCRIPTION_CHARS = 12_000
MAX_FIT_REASONING_CHARS = 1_500
MAX_THREAD_MESSAGE_CHARS = 4_000


def _cap(text: str, limit: int) -> str:
    return text[:limit] if len(text) > limit else text


@dataclass(frozen=True)
class DraftResult:
    """A draft plus the evidence of what the checks found, so the caller can record it."""

    body: str
    first_failures: list[Failure]
    final_failures: list[Failure]
    retried: bool


def _generate_checked(prompt: str, check: Callable[[str], list[Failure]]) -> DraftResult:
    """Generate, check the draft against the deterministic rules, and give the model one chance to
    fix what it broke.

    The prompts already state every rule this checks, and they are followed most of the time but
    not always -- long prompts leak. One retry costs one extra call only when something is actually
    wrong, and if the retry is no better we keep whichever draft broke fewer rules rather than
    failing the request: a flawed draft you can edit beats no draft at all.

    Returns the failures rather than swallowing them: without that record you cannot tell which
    drafts needed fixing, which rules leak most often, or whether a prompt edit helped.
    """
    client = get_llm_client()
    body = client.generate(system=_COPYWRITER_SYSTEM_PROMPT, user=prompt).strip()
    failures = check(body)
    if not failures:
        return DraftResult(body, [], [], retried=False)

    correction = (
        f"{prompt}\n\nYou already wrote this draft:\n{body}\n\n"
        "It breaks rules you were given:\n"
        + "\n".join(f"- {failure['detail']}" for failure in failures)
        + "\n\nWrite it again, fixing exactly those problems and changing nothing else. "
        "Output only the message text."
    )
    retry = client.generate(system=_COPYWRITER_SYSTEM_PROMPT, user=correction).strip()
    retry_failures = check(retry)

    if len(retry_failures) < len(failures):
        return DraftResult(retry, failures, retry_failures, retried=True)
    return DraftResult(body, failures, failures, retried=True)


def _lead_text(lead: Lead) -> str:
    description = _cap(lead.description, MAX_DESCRIPTION_CHARS)
    return f"Title: {lead.title}\nURL: {lead.url}\nAuthor: {lead.author}\n\n{description}"


def _thread_text(thread: list[OutreachMessage]) -> str:
    return "\n".join(
        f"{'me' if m.sender == 'me' else 'them'}: {_cap(m.body, MAX_THREAD_MESSAGE_CHARS)}" for m in thread
    )


def run_fit_check(lead: Lead) -> tuple[str, str, str | None]:
    prompt = load_prompt(
        "fit_check",
        positioning=SELF_POSITIONING,
        resume_text=get_skills_text(),
        # The index, not the full catalogue: this decides whether a lead is worth approaching,
        # which needs the shape of what he has built, never the build detail.
        projects_text=projects_index(get_projects_text()),
        lead_text=_lead_text(lead),
    )
    response = get_llm_client().generate(system="You are a precise, honest fit-assessment assistant.", user=prompt)

    verdict_match = VERDICT_PATTERN.search(response)
    reasoning_match = REASONING_PATTERN.search(response)
    lead_type_match = LEAD_TYPE_PATTERN.search(response)
    verdict = verdict_match.group(1).lower() if verdict_match else "maybe"
    # REASONING is captured DOTALL to the end, so strip a LEAD_TYPE line that follows it rather
    # than swallowing it into the prose the UI shows.
    reasoning = reasoning_match.group(1).strip() if reasoning_match else response.strip()
    reasoning = LEAD_TYPE_PATTERN.sub("", reasoning).strip()
    # None rather than a guess when the model omits it: an unknown type should read as unknown, not
    # be silently bucketed as "other" and then counted as evidence in episode grouping.
    lead_type = lead_type_match.group(1).lower() if lead_type_match else None
    return verdict, reasoning, lead_type


def draft_connection_note(lead: Lead, fit_reasoning: str) -> DraftResult:
    prompt = load_prompt(
        "connection_note",
        positioning=SELF_POSITIONING,
        resume_text=get_skills_text(),
        lead_text=_lead_text(lead),
        fit_reasoning=_cap(fit_reasoning, MAX_FIT_REASONING_CHARS),
    )
    return _generate_checked(prompt, check_connection_note)


def draft_next_message(
    lead: Lead,
    thread: list[OutreachMessage],
    fit_reasoning: str,
    origin_type: str,
    stage_purpose: str,
    message_count: int,
    is_soft_close: bool = False,
    past_outreach: str = "",
    learned_guidance: str = "",
) -> DraftResult:
    """Drafts the next message in the post-connection sequence -- covers both the first real
    message and every subsequent follow-up, since they're one continuous sequence (intro ->
    show my work -> direct ask -> soft close), not structurally different
    actions. `message_count` is how many staged messages have already gone out, and is what
    decides first-vs-follow-up -- `thread` may already hold a reply from them even at zero."""
    lead_text = _lead_text(lead)
    projects_text = select_projects(
        get_projects_text(),
        exclude_mentioned_in="\n".join(m.body for m in thread if m.sender == "me"),
    )
    prompt = load_prompt(
        "outreach_message",
        positioning=SELF_POSITIONING,
        resume_text=get_skills_text(),
        projects_text=projects_text,
        lead_text=lead_text,
        fit_reasoning=_cap(fit_reasoning, MAX_FIT_REASONING_CHARS),
        origin_guidance=ORIGIN_GUIDANCE.get(origin_type, ORIGIN_GUIDANCE["prospected"]),
        ask_guidance=ASK_GUIDANCE,
        thread_text=_thread_text(thread),
        stage_purpose=stage_purpose,
        position_guidance=POSITION_GUIDANCE["first" if message_count == 0 else "follow_up"],
        past_outreach=past_outreach or "No comparable past outreach yet. Ignore this section.",
        learned_guidance=learned_guidance or "Nothing learned yet: too few outreaches have a known outcome.",
    )
    return _generate_checked(
        prompt,
        lambda body: check_message(
            body,
            projects_text=projects_text,
            previous_me_messages=tuple(m.body for m in thread if m.sender == "me"),
            is_soft_close=is_soft_close,
        ),
    )


def generate_reflection(episodes_text: str, summary_text: str) -> str:
    """Distil what past outreach taught into guidance for future drafts.

    Not run through _generate_checked: the output is internal guidance for the prompts, not a
    message to a human, so none of the message rules (word count, links, dashes) apply to it.
    """
    prompt = load_prompt("reflection", episodes_text=episodes_text, summary_text=summary_text)
    return get_llm_client().generate(
        system="You are a careful analyst. You never claim more than the data supports.", user=prompt
    ).strip()


def revise_message(
    lead: Lead,
    thread: list[OutreachMessage],
    current_draft: str,
    instruction: str,
    *,
    is_soft_close: bool = False,
) -> DraftResult:
    """Re-run one existing draft with a human instruction applied ("drop the last line", "shorter").

    `thread` must exclude the draft being revised -- it is passed separately, and showing it twice
    invites the model to treat its own text as part of the conversation.

    The checks still run. An instruction can legitimately override a prompt rule (the prompt says
    so), but it cannot quietly reintroduce an em dash or a repo link, so those stay enforced.
    """
    # Index only: a revision keeps whichever project the draft already names, so it needs the
    # attribution and sharing rules but never the build detail of fourteen other projects.
    projects_text = projects_index(get_projects_text())
    prompt = load_prompt(
        "revise_message",
        positioning=SELF_POSITIONING,
        resume_text=get_skills_text(),
        projects_text=projects_text,
        lead_text=_lead_text(lead),
        thread_text=_thread_text(thread),
        current_draft=current_draft,
        instruction=instruction.strip(),
    )
    # Deliberately no `previous_me_messages`: the repeated-project rule exists to stop a follow-up
    # recycling material, but a revision is the SAME message said differently, so its project is
    # already in the thread by definition. Passing them made "make it shorter" trip the rule and the
    # retry "fixed" it by silently swapping to a different project, which is not what was asked.
    return _generate_checked(
        prompt,
        lambda body: check_message(body, projects_text=projects_text, is_soft_close=is_soft_close),
    )


def suggest_reply(lead: Lead, thread: list[OutreachMessage], fit_reasoning: str = "") -> DraftResult:
    lead_text = _lead_text(lead)
    projects_text = get_projects_text()
    prompt = load_prompt(
        "reply_suggestion",
        positioning=SELF_POSITIONING,
        resume_text=get_skills_text(),
        projects_text=projects_text,
        lead_text=lead_text,
        fit_reasoning=_cap(fit_reasoning, MAX_FIT_REASONING_CHARS)
        or "No fit assessment on record for this lead.",
        ask_guidance=ASK_GUIDANCE,
        thread_text=_thread_text(thread),
    )
    # Repeated-project is off here: if they asked about a project by name, naming it back is the
    # answer. Repeated-portfolio stays on -- they already have the link.
    return _generate_checked(
        prompt,
        lambda body: check_message(
            body,
            projects_text=projects_text,
            previous_me_messages=tuple(m.body for m in thread if m.sender == "me"),
            check_repeated_project=False,
        ),
    )


def _parse_email(raw: str) -> tuple[str, str]:
    """Splits the model's SUBJECT:/BODY: output into its two parts.

    Falls back to treating the whole response as the body with an empty subject rather than raising,
    so a model that drops the SUBJECT: line still produces something a human can fix instead of a
    500. The check will flag the empty subject either way.
    """
    subject_match = EMAIL_SUBJECT_PATTERN.search(raw)
    body_match = EMAIL_BODY_PATTERN.search(raw)
    subject = subject_match.group(1).strip() if subject_match else ""
    body = body_match.group(1).strip() if body_match else raw.strip()
    return subject, body


# email_outreach.md tells the model "the system appends the rest" and to write no sign-off of its
# own -- this is that system-side append. Bug fixed 11 Oct 2026: the prompt made this promise before
# any code actually kept it, so every email would have stored with no signature at all.
#
# No dash: this is appended AFTER check_email() runs, so the no-dash rule never sees it -- a dash
# here would be a silent, permanent AI tell on every single email, worse than one check could ever
# catch since it's not even visible to the thing meant to catch it.
#
# No portfolio link: hassanmehmood.online is deliberately left out of the cold-email signature.
# Spam filters score a .online TLD against a message during mailbox warm-up, and the portfolio link
# already appears in LinkedIn messages where that risk doesn't apply -- LinkedIn is the right place
# for it, not a fresh cold-sending domain's first impression.
#
# linkedin.com/in/hassan-mehmood-346954243 is the real profile URL (confirmed directly), not the
# short vanity slug -- a slug that short is exactly the kind that's easy to assume and wrong.
EMAIL_SIGNATURE = """Hassan Mehmood
AI & Automation for E-commerce and SaaS
linkedin.com/in/hassan-mehmood-346954243
Lahore, Pakistan"""


def _format_email(subject: str, body: str) -> str:
    """Combines subject, body and the real signature into the single string OutreachMessage.body
    stores.

    No separate `subject` column: a cold email is still conceptually one message, and the stored
    form just carries its subject as a labelled first line, which the UI can split back out to
    render distinctly for channel == "email" without the schema needing a second text column.
    """
    return f"Subject: {subject}\n\n{body}\n\n{EMAIL_SIGNATURE}"


def _generate_checked_email(prompt: str) -> DraftResult:
    """Generate-check-retry for email, mirroring _generate_checked but over a (subject, body) pair
    instead of a single string, since check_email needs both to validate the subject line.

    Stores the combined "Subject: ...\\n\\n<body>" form in DraftResult.body either way, so every
    other piece of code that handles a DraftResult (recording checks, saving the message) needs no
    email-specific branch.
    """
    client = get_llm_client()
    raw = client.generate(system=_EMAIL_SYSTEM_PROMPT, user=prompt).strip()
    subject, body = _parse_email(raw)
    failures = check_email(subject, body)
    if not failures:
        return DraftResult(_format_email(subject, body), [], [], retried=False)

    correction = (
        f"{prompt}\n\nYou already wrote this draft:\nSUBJECT: {subject}\nBODY:\n{body}\n\n"
        "It breaks rules you were given:\n"
        + "\n".join(f"- {failure['detail']}" for failure in failures)
        + "\n\nWrite it again, fixing exactly those problems and changing nothing else. "
        "Output in the same SUBJECT:/BODY: format."
    )
    retry_raw = client.generate(system=_EMAIL_SYSTEM_PROMPT, user=correction).strip()
    retry_subject, retry_body = _parse_email(retry_raw)
    retry_failures = check_email(retry_subject, retry_body)

    if len(retry_failures) < len(failures):
        return DraftResult(_format_email(retry_subject, retry_body), failures, retry_failures, retried=True)
    return DraftResult(_format_email(subject, body), failures, failures, retried=True)


def draft_email(
    lead: Lead,
    thread: list[OutreachMessage],
    fit_reasoning: str,
    origin_type: str,
    follow_up_stage: str = "opening",
) -> DraftResult:
    """Drafts a cold email: the opening touch (follow_up_stage="opening") or one of the two
    follow-ups ("value_add" for day 4, "clear_ask" for day 10) from
    _internal/Client_Acquisition_Plan.md's Cold Outreach Playbook. See FOLLOW_UP_GUIDANCE.

    `thread` holds only "me"/channel=="email" and "them" messages the caller has chosen to show --
    typically the prior email(s) on this lead, not the LinkedIn thread, so the model isn't asked to
    treat a LinkedIn connection note as part of the same conversation.
    """
    prompt = load_prompt(
        "email_outreach",
        positioning=SELF_POSITIONING,
        resume_text=get_skills_text(),
        projects_text=get_projects_text(),
        lead_text=_lead_text(lead),
        fit_reasoning=_cap(fit_reasoning, MAX_FIT_REASONING_CHARS)
        or "No fit assessment on record for this lead.",
        origin_guidance=ORIGIN_GUIDANCE.get(origin_type, ORIGIN_GUIDANCE["prospected"]),
        ask_guidance=ASK_GUIDANCE,
        thread_text=_thread_text(thread) or "No emails sent to this lead yet.",
        follow_up_guidance=FOLLOW_UP_GUIDANCE.get(follow_up_stage, FOLLOW_UP_GUIDANCE["opening"]),
    )
    return _generate_checked_email(prompt)
