from pathlib import Path

_PROMPTS_DIR = Path(__file__).resolve().parent


def load_prompt(name: str, **kwargs: str) -> str:
    template = (_PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")
    return template.format(**kwargs)
