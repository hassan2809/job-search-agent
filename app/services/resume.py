import re
from functools import lru_cache
from pathlib import Path

from pypdf import PdfReader

from app.core.config import settings


class ResumeNotFoundError(Exception):
    pass


@lru_cache(maxsize=1)
def get_resume_text() -> str:
    resume_path = Path(__file__).resolve().parents[2] / settings.resume_path
    resume_path = resume_path.resolve()

    if not resume_path.exists():
        raise ResumeNotFoundError(f"Resume not found at {resume_path}")

    reader = PdfReader(str(resume_path))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages).strip()


_SKILLS_START = re.compile(r"^Technical Skills\s*$", re.M)
_SKILLS_END = re.compile(r"^(Certifications|Education|Projects|Work Experience)\s*$", re.M)


@lru_cache(maxsize=1)
def get_skills_text() -> str:
    """Just the Technical Skills block from the resume.

    The rest of the resume is either duplicated by the project catalogue (the same three projects,
    the same bullets) or irrelevant to writing a message (contact details, certifications, dates).
    Sending it whole cost around 950 tokens per draft to repeat what the catalogue already says
    better. Skills are the one part the catalogue does not carry in a scannable form.

    Falls back to the full resume if the heading isn't found, so an unexpected PDF layout degrades
    to the old behaviour rather than silently sending the model nothing about my background.
    """
    resume = get_resume_text()
    start = _SKILLS_START.search(resume)
    if not start:
        return resume
    rest = resume[start.end() :]
    end = _SKILLS_END.search(rest)
    return "Technical Skills\n" + (rest[: end.start()] if end else rest).strip()


def select_projects(projects_text: str, *, exclude_mentioned_in: str = "") -> str:
    """Drop projects already used in this thread, and send the rest.

    This deliberately does NOT rank by relevance to the lead. Keyword ranking was tried and was
    measurably worse than letting the model choose: a payments company's profile can talk about
    "merchants" and "fintech" without ever using the word "payments", so the payment-gateway project
    scores zero while a crypto dashboard wins on the word "fintech". Choosing which of my projects
    speaks to a given company is a judgement about meaning, and the model is better at it -- given
    the whole catalogue it has reliably picked well. Hiding candidates from it to save tokens trades
    the quality of the message for a cost saving, which is the wrong way round.

    Exclusion is different: it is exact string matching over what has already been sent, no
    judgement involved, and it makes "never re-use a project" a property of what the model can see
    rather than an instruction it has to remember.
    """
    if not projects_text or not exclude_mentioned_in:
        return projects_text

    tail_at = projects_text.find("\n# Context")
    tail = projects_text[tail_at:] if tail_at != -1 else ""
    main = projects_text[:tail_at] if tail_at != -1 else projects_text

    head, separator, rest = main.partition("\n## ")
    if not separator:
        return projects_text

    kept = [
        f"## {section}".rstrip()
        for section in rest.split("\n## ")
        if not re.search(
            rf"\b{re.escape(section.splitlines()[0].strip())}\b", exclude_mentioned_in, re.IGNORECASE
        )
    ]
    return "\n\n".join([head.rstrip(), *kept]) + ("\n" + tail if tail else "")


@lru_cache(maxsize=1)
def get_projects_text() -> str:
    """The full project catalogue, which the resume PDF does not carry -- it lists three projects
    where the portfolio has twelve. Without this the drafts kept recycling the same two or three,
    which is exactly what makes a follow-up sequence read as automated. Optional: returns "" if the
    file isn't there, so outreach still works on the resume alone."""
    projects_path = (Path(__file__).resolve().parents[2] / settings.projects_path).resolve()
    if not settings.projects_path or not projects_path.exists():
        return ""
    return projects_path.read_text(encoding="utf-8").strip()
