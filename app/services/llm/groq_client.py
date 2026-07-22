from groq import Groq

from app.core.config import settings
from app.services.llm.client import LLMClient

MODEL = "openai/gpt-oss-120b"


class GroqLLMClient(LLMClient):
    def __init__(self) -> None:
        self._client = Groq(api_key=settings.groq_api_key)

    def generate(self, system: str, user: str) -> str:
        response = self._client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return response.choices[0].message.content
