import re
from collections.abc import Callable
from dataclasses import dataclass

from app.core.prompts import load_prompt
from app.models.lead import Lead
from app.models.outreach import OutreachMessage
from app.services.llm.client import get_llm_client
from app.services.message_checks import Failure, check_connection_note, check_message
from app.services.resume import get_projects_text, get_skills_text, projects_index, select_projects

VERDICT_PATTERN = re.compile(r"VERDICT:\s*(good_fit|maybe|not_a_fit)", re.IGNORECASE)
REASONING_PATTERN = re.compile(r"REASONING:\s*(.+)", re.IGNORECASE | re.DOTALL)
LEAD_TYPE_PATTERN = re.compile(
    r"LEAD_TYPE:\s*(builds_software|sells_services|recruiter|creator|other)", re.IGNORECASE
)

# Injected into every prompt. The resume alone doesn't say what I'm doing on LinkedIn, so without
# this the model reads big platform numbers off it and writes as though I were an agency selling
# services -- offering to audit a stranger's systems, claiming their scale as my own results.
SELF_POSITIONING = """WHO I AM (this governs the tone -- do not drift from it):
I am one developer, roughly two years into my career, employed as a full-stack developer building
client products at a small agency. I am looking for a job, a contract, or project work. I am NOT an
agency or a consultancy, and there is no team behind me.

- Never write as a vendor. Never offer to audit, review, or produce a report, checklist or
  recommendation on how someone should run their business: from me to someone senior that reads as
  presumptuous and gets ignored.
- What I offer is specific technical relief, not broad transformation. The slow page, the
  integration that keeps breaking, the backlog nobody has had time to clear. Narrow and real beats
  sweeping and vague.
- Being solo is a real advantage, worth saying plainly where it fits: no agency overhead, direct
  access to the person writing the code, current frameworks, one project at a time rather than ten.
  Never a dig at agencies, never a boast.
- Being early in my career is neither hidden nor apologised for. Specific beats impressive.
- The resume's numbers ($3M+ monthly, 50,000+ shipments, 60% faster) are the scale of PLATFORMS I
  worked on as one developer on a team, never results I delivered. "I built the inbound and refunds
  modules" is true; "I handle $3M+ monthly with end-to-end reconciliation" is not.
- The catalogue is the authority on which employer each project belongs to. Where it says
  "Employer: not stated", name the project on its own and invent nothing.
- One project per message, the most relevant one. Never a list, never a tour of my resume.
- The only links are my portfolio, hassanmehmood.online, and a "Live:" product URL from the
  catalogue. Never a repository, never an offer to send code. A link that is in the message has
  already been sent, so do not also ask permission to send it.
- What I am asking for is work: are they hiring, do they need a developer, would they look at what
  I have built. Never a discovery call, an audit, or a strategy conversation."""

ORIGIN_GUIDANCE = {
    "disclosed_need": "They publicly stated a need -- reference their specific stated need directly.",
    "prospected": (
        "This is a cold outreach to someone who has NOT publicly stated a need -- lead with the "
        "concrete overlap between my skills and what they/their company work on, not a generic pitch."
    ),
}

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

# These two rules kept getting ignored as bullets near the end of a long user prompt, so they live
# here instead -- system position carries far more weight, and all three copy prompts share it.
_COPYWRITER_SYSTEM_PROMPT = """You are a concise, specific outreach copywriter writing on behalf of \
one solo full-stack developer looking for freelance work, contracts, or a job. Relevance over volume.

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


def suggest_reply(lead: Lead, thread: list[OutreachMessage]) -> DraftResult:
    lead_text = _lead_text(lead)
    projects_text = get_projects_text()
    prompt = load_prompt(
        "reply_suggestion",
        positioning=SELF_POSITIONING,
        resume_text=get_skills_text(),
        projects_text=projects_text,
        lead_text=lead_text,
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
