from __future__ import annotations

from decimal import Decimal
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="IC_",
        env_file=".env",
        extra="ignore",
    )

    database_url: str = "postgresql+psycopg://copilot:copilot@localhost:5432/copilot"
    t_amount: Decimal = Decimal("10000")
    tolerance_pct: Decimal = Decimal("0.05")
    learn_min_corrections: int = 3
    duplicate_window_days: int = 14
    cold_start_n: int = 2
    storage_dir: str = "./storage"

    # LLM provider settings
    llm_provider: str = "mock"
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-4-6"
    openai_model: str = "gpt-4o"


@lru_cache
def get_settings() -> Settings:
    return Settings()
