import re

from app.core.prompts import load_prompt
from app.models.lead import Lead
from app.models.outreach import OutreachMessage
from app.services.llm.client import get_llm_client
from app.services.resume import get_projects_text, get_resume_text

VERDICT_PATTERN = re.compile(r"VERDICT:\s*(good_fit|maybe|not_a_fit)", re.IGNORECASE)
REASONING_PATTERN = re.compile(r"REASONING:\s*(.+)", re.IGNORECASE | re.DOTALL)

# Injected into every prompt. The resume alone doesn't say what I'm doing on LinkedIn, so without
# this the model reads big platform numbers off it and writes as though I were an agency selling
# services -- offering to audit a stranger's systems, claiming their scale as my own results.
SELF_POSITIONING = """WHO I AM (this governs the tone -- do not drift from it):
I am one developer, roughly two years into my career, currently employed as a full-stack developer
building client products at a small agency. I am looking for a job, a contract, or project work.
I am NOT an agency, a consultancy, or a founder selling a service. There is no team behind me.

What follows from that:
- Never write as a vendor pitching services. Never offer to audit, review, assess, or produce a
  report, checklist or recommendation on how someone should run their business. Coming from someone
  at my level to someone senior, that reads as presumptuous and gets ignored.
- The numbers in my resume ($3M+ monthly volume, 50,000+ shipments, 60% faster processing) describe
  the SCALE OF PLATFORMS I WORKED ON as one developer on a team. They are not results I personally
  delivered to a client, and not evidence I can operate at that scale on my own. Reference what I
  actually built and the stack I used. Never imply I own those business outcomes.
- Concretely: "I built the inbound and refunds modules of an e-commerce ops platform" is true and
  worth saying. "I handle $3M+ monthly with end-to-end reconciliation" is not.
- Being early in my career is not something to hide, and not something to apologise for either.
  Straightforward and specific beats impressive.
- What I am asking for is work: whether they are hiring, whether they need a developer on something,
  or whether they would take a look at what I have built. Never a discovery call, an audit, or a
  strategy conversation.
- What I share is my portfolio, hassanmehmood.online. That is the default and usually the only link
  worth including. The public site of a product I worked on is fine too where the catalogue lists a
  "Live:" URL. Never a GitHub repo and never an offer to send code, whatever its licence or
  visibility.
- Mention ONE project per message, the single most relevant one, named with the employer I built it
  at. Never list several. Walking through my resume is a resume dump and it reads as self-focused
  however accurate it is.
- Never merge two jobs or two projects into one claim. The project catalogue below states which
  employer each project belongs to, and it is the authority on that. Writing "gateway integrations
  and the refunds modules for eCom Central" welds KloudPlugins work onto a DeveloperTag product --
  a factual error the reader can catch, and the fastest way to look like I am padding.
- Where the catalogue says "Employer: not stated", do not invent one. Name the project on its own
  ("I built Guard XP, a multi-tenant operations app..."). If it does not say where something was
  built, neither do I.
- Never ask permission to send something the message already contains. If the portfolio link is in
  the text then it is sent, so "may I send my portfolio (hassanmehmood.online)?" contradicts itself.
  Pick one: either drop the link in plainly ("my portfolio is at hassanmehmood.online if it's
  useful"), or ask whether they'd like to see it and leave the link out. Including it plainly is
  usually better -- it is one public URL, and making someone grant permission for a link they can
  already click is needless ceremony.
- Never link a repository and never offer to send code, for any project, public or not. No
  github.com links, no "happy to share the repo", no "the code is on my GitHub". The portfolio is
  what I point people at, and a "Live:" product URL from the catalogue is the only other link that
  belongs in a message."""

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
        "I have already sent at least one staged message. This is a follow-up: continue naturally, "
        "add something new rather than repeating what has already been said, and keep it noticeably "
        "shorter and lower-effort to read than a first message -- a nudge, not a re-pitch. A "
        "follow-up that only says 'just following up' gives them nothing to react to. Reference the "
        "earlier message briefly, bring one genuinely new thing, then one easy question. Repeating "
        "myself is the fastest way to look automated, so two things must be fresh every time:\n"
        "  - The HOOK. Do not open on the same detail about them that an earlier message already "
        "used. If the first message led on a conference talk, this one leads on something else in "
        "the lead text: a different post, a company update, an open role, an opinion they stated, "
        "how they describe their team. Read what I already opened with, then pick different "
        "material.\n"
        "  - The PROJECT. Never re-use one I have already mentioned in this conversation. Reach for "
        "a different piece of my background.\n"
        "  - The CLOSING QUESTION. Do not re-send a question I have already asked. If I have "
        "already asked who the right person to speak to is, asking it again is nagging, not a "
        "follow-up.\n"
        "If the lead text genuinely offers no second angle, say less rather than repeat the first "
        "one -- a short, honest nudge beats a reworded copy of the previous message.\n"
        "None of the above applies if THIS MESSAGE'S PURPOSE is a soft close. A close brings no new "
        "project and no new question at all; the purpose overrides everything here."
    ),
}

# These two rules kept getting ignored as bullets near the end of a long user prompt, so they live
# here instead -- system position carries far more weight, and all three copy prompts share it.
_COPYWRITER_SYSTEM_PROMPT = """You are a concise, specific outreach copywriter writing on behalf of \
one solo developer looking for work. Relevance over volume.

Two rules override everything else in the user message:

1. NEVER use a dash as punctuation. No em dash, no en dash, and no hyphen standing in for one. This \
is the single clearest giveaway of AI-written text and it gets the message ignored. Use a comma, a \
full stop, or two shorter sentences instead. Hyphens inside ordinary compound words (full-stack, \
end-to-end, human-in-the-loop) are fine and should be left alone. Note that the user message uses \
double hyphens in its own instructions; that is formatting for you, never a licence to use dashes \
in the message you write.

2. When referring to work he has built, point at something the reader can actually CHECK, not just \
a description: his portfolio at hassanmehmood.online, or the live site of a product he worked on. \
Verifiable beats impressive. NEVER link a code repository and never offer to send code. No \
github.com links of any kind, regardless of whether a repo is public.

Output only the message text itself. No preamble, no subject line, no explanation."""
MAX_DESCRIPTION_CHARS = 12_000
MAX_FIT_REASONING_CHARS = 1_500
MAX_THREAD_MESSAGE_CHARS = 4_000


def _cap(text: str, limit: int) -> str:
    return text[:limit] if len(text) > limit else text


def _lead_text(lead: Lead) -> str:
    description = _cap(lead.description, MAX_DESCRIPTION_CHARS)
    return f"Title: {lead.title}\nURL: {lead.url}\nAuthor: {lead.author}\n\n{description}"


def _thread_text(thread: list[OutreachMessage]) -> str:
    return "\n".join(
        f"{'me' if m.sender == 'me' else 'them'}: {_cap(m.body, MAX_THREAD_MESSAGE_CHARS)}" for m in thread
    )


def run_fit_check(lead: Lead) -> tuple[str, str]:
    prompt = load_prompt(
        "fit_check",
        positioning=SELF_POSITIONING,
        resume_text=get_resume_text(),
        projects_text=get_projects_text(),
        lead_text=_lead_text(lead),
    )
    response = get_llm_client().generate(system="You are a precise, honest fit-assessment assistant.", user=prompt)

    verdict_match = VERDICT_PATTERN.search(response)
    reasoning_match = REASONING_PATTERN.search(response)
    verdict = verdict_match.group(1).lower() if verdict_match else "maybe"
    reasoning = reasoning_match.group(1).strip() if reasoning_match else response.strip()
    return verdict, reasoning


def draft_connection_note(lead: Lead, fit_reasoning: str) -> str:
    prompt = load_prompt(
        "connection_note",
        positioning=SELF_POSITIONING,
        resume_text=get_resume_text(),
        lead_text=_lead_text(lead),
        fit_reasoning=_cap(fit_reasoning, MAX_FIT_REASONING_CHARS),
    )
    return get_llm_client().generate(system=_COPYWRITER_SYSTEM_PROMPT, user=prompt).strip()


def draft_next_message(
    lead: Lead,
    thread: list[OutreachMessage],
    fit_reasoning: str,
    origin_type: str,
    stage_purpose: str,
    message_count: int,
) -> str:
    """Drafts the next message in the post-connection sequence -- covers both the first real
    message and every subsequent follow-up, since they're one continuous sequence (intro ->
    show my work -> direct ask -> soft close), not structurally different
    actions. `message_count` is how many staged messages have already gone out, and is what
    decides first-vs-follow-up -- `thread` may already hold a reply from them even at zero."""
    prompt = load_prompt(
        "outreach_message",
        positioning=SELF_POSITIONING,
        resume_text=get_resume_text(),
        projects_text=get_projects_text(),
        lead_text=_lead_text(lead),
        fit_reasoning=_cap(fit_reasoning, MAX_FIT_REASONING_CHARS),
        origin_guidance=ORIGIN_GUIDANCE.get(origin_type, ORIGIN_GUIDANCE["prospected"]),
        thread_text=_thread_text(thread),
        stage_purpose=stage_purpose,
        position_guidance=POSITION_GUIDANCE["first" if message_count == 0 else "follow_up"],
    )
    return get_llm_client().generate(system=_COPYWRITER_SYSTEM_PROMPT, user=prompt).strip()


def suggest_reply(lead: Lead, thread: list[OutreachMessage]) -> str:
    prompt = load_prompt(
        "reply_suggestion",
        positioning=SELF_POSITIONING,
        resume_text=get_resume_text(),
        projects_text=get_projects_text(),
        lead_text=_lead_text(lead),
        thread_text=_thread_text(thread),
    )
    return get_llm_client().generate(system=_COPYWRITER_SYSTEM_PROMPT, user=prompt).strip()
