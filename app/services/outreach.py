import re

from app.core.prompts import load_prompt
from app.models.lead import Lead
from app.models.outreach import OutreachMessage
from app.services.llm.client import get_llm_client
from app.services.resume import get_resume_text

VERDICT_PATTERN = re.compile(r"VERDICT:\s*(good_fit|maybe|not_a_fit)", re.IGNORECASE)
REASONING_PATTERN = re.compile(r"REASONING:\s*(.+)", re.IGNORECASE | re.DOTALL)

ORIGIN_GUIDANCE = {
    "disclosed_need": "They publicly stated a need -- reference their specific stated need directly.",
    "prospected": (
        "This is a cold outreach to someone who has NOT publicly stated a need -- lead with the "
        "concrete overlap between my skills and what they/their company work on, not a generic pitch."
    ),
}

_COPYWRITER_SYSTEM_PROMPT = "You are a concise, specific outreach copywriter. Relevance over volume."
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
    prompt = load_prompt("fit_check", resume_text=get_resume_text(), lead_text=_lead_text(lead))
    response = get_llm_client().generate(system="You are a precise, honest fit-assessment assistant.", user=prompt)

    verdict_match = VERDICT_PATTERN.search(response)
    reasoning_match = REASONING_PATTERN.search(response)
    verdict = verdict_match.group(1).lower() if verdict_match else "maybe"
    reasoning = reasoning_match.group(1).strip() if reasoning_match else response.strip()
    return verdict, reasoning


def draft_connection_note(lead: Lead, fit_reasoning: str) -> str:
    prompt = load_prompt(
        "connection_note",
        resume_text=get_resume_text(),
        lead_text=_lead_text(lead),
        fit_reasoning=_cap(fit_reasoning, MAX_FIT_REASONING_CHARS),
    )
    return get_llm_client().generate(system=_COPYWRITER_SYSTEM_PROMPT, user=prompt).strip()


def draft_next_message(
    lead: Lead, thread: list[OutreachMessage], fit_reasoning: str, origin_type: str, stage_purpose: str
) -> str:
    """Drafts the next message in the post-connection sequence -- covers both the first real
    message and every subsequent follow-up, since they're one continuous sequence (value
    proposition -> case study -> solution proposal -> soft close), not structurally different
    actions. `thread` is empty for the first message."""
    prompt = load_prompt(
        "outreach_message",
        resume_text=get_resume_text(),
        lead_text=_lead_text(lead),
        fit_reasoning=_cap(fit_reasoning, MAX_FIT_REASONING_CHARS),
        origin_guidance=ORIGIN_GUIDANCE.get(origin_type, ORIGIN_GUIDANCE["prospected"]),
        thread_text=_thread_text(thread),
        stage_purpose=stage_purpose,
    )
    return get_llm_client().generate(system=_COPYWRITER_SYSTEM_PROMPT, user=prompt).strip()


def suggest_reply(lead: Lead, thread: list[OutreachMessage]) -> str:
    prompt = load_prompt(
        "reply_suggestion",
        resume_text=get_resume_text(),
        lead_text=_lead_text(lead),
        thread_text=_thread_text(thread),
    )
    return get_llm_client().generate(system=_COPYWRITER_SYSTEM_PROMPT, user=prompt).strip()
