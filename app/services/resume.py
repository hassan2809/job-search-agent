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
