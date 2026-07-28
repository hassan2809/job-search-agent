from openai import OpenAI

from app.core.config import settings
from app.services.llm.client import LLMClient

MODEL = "gpt-5-mini"


class OpenAILLMClient(LLMClient):
    def __init__(self) -> None:
        self._client = OpenAI(api_key=settings.openai_api_key)

    def generate(self, system: str, user: str) -> str:
        response = self._client.responses.create(
            model=MODEL,
            instructions=system,
            input=user,
        )
        return response.output_text
