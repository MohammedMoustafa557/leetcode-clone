from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "CodeArena API"
    database_url: str = "postgresql+psycopg://leetcode:leetcode@localhost:5432/leetcode"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 60 * 24 * 7
    cors_origins: str = "http://localhost:5173,http://localhost:8080"

    # Optional: OpenAI-compatible LLM for richer per-problem guides (cached in the DB).
    llm_api_key: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"

    # Weekly contest: contest #1 starts on contest_first_date at contest_start_utc (default Fri 16:00 UTC = 18:00 Cairo)
    contest_first_date: str = "2026-01-02"
    contest_start_utc: str = "16:00"
    contest_minutes: int = 90

    # Optional: push first-time solves of ONE user to a Notion database (off by default).
    notion_token: str = ""
    notion_database_id: str = ""
    notion_sync_username: str = ""
    public_site_url: str = "http://localhost:8080"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
