from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = ""
    resume_path: str = ""
    # Full project catalogue -- the resume PDF only carries a few. Optional; outreach falls back to
    # the resume alone if this file is missing.
    projects_path: str = "shared-data/projects.md"

    # LLM provider -- see app/services/llm/client.py's factory.
    llm_provider: str = ""
    groq_api_key: str = ""
    openai_api_key: str = ""


settings = Settings()
