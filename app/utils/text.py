import re

EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")


def extract_self_disclosed_email(text: str) -> str | None:
    """Only pulls an email if it's directly present in the given text."""
    match = EMAIL_PATTERN.search(text or "")
    return match.group(0) if match else None


def derive_title(raw_content: str, length: int = 100) -> str:
    """Best-effort title from raw pasted content, without needing an LLM call."""
    first_line = (raw_content or "").strip().splitlines()[0] if raw_content.strip() else ""
    return first_line[:length].strip() or "Untitled lead"
