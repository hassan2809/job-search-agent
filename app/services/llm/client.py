from abc import ABC, abstractmethod

from app.core.config import settings


class LLMNotConfiguredError(Exception):
    """Raised when no LLM provider has been chosen yet in settings."""


class LLMClient(ABC):
    @abstractmethod
    def generate(self, system: str, user: str) -> str:
        """Returns the model's raw text response to a single-turn prompt."""


def get_llm_client() -> LLMClient:
    provider = settings.llm_provider.strip().lower()

    if provider == "groq":
        from app.services.llm.groq_client import GroqLLMClient

        return GroqLLMClient()

    raise LLMNotConfiguredError(
        "No LLM provider configured yet. Set LLM_PROVIDER=groq (plus GROQ_API_KEY) in .env -- "
        "everything that calls the LLM (fit-check, drafting, reply suggestions) will work as soon "
        "as this is set, no other code changes needed."
    )
