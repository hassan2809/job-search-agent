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

    if provider == "anthropic":
        from app.services.llm.anthropic_client import AnthropicLLMClient

        return AnthropicLLMClient()

    if provider == "openai":
        from app.services.llm.openai_client import OpenAILLMClient

        return OpenAILLMClient()

    raise LLMNotConfiguredError(
        "No LLM provider configured yet. Set LLM_PROVIDER=anthropic|openai (plus the matching "
        "API key) in .env once a provider is chosen -- everything that calls the LLM (fit-check, "
        "drafting, reply suggestions) will work as soon as this is set, no other code changes needed."
    )
