from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./leads.db"
    resume_path: str = "../Hassan_Mehmood_Resume.pdf"

    # LLM provider is intentionally undecided -- see app/services/llm/client.py.
    llm_provider: str = ""


settings = Settings()
