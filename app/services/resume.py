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
