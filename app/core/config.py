from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = ""
    resume_path: str = ""

    # LLM provider -- see app/services/llm/client.py's factory.
    llm_provider: str = ""
    groq_api_key: str = ""


settings = Settings()
