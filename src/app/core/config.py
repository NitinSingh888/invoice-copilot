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

    database_url: str = "sqlite:///./invoice_copilot.db"
    t_amount: Decimal = Decimal("10000")
    tolerance_pct: Decimal = Decimal("0.05")
    learn_min_corrections: int = 3
    duplicate_window_days: int = 14
    cold_start_n: int = 2
    storage_dir: str = "./storage"


@lru_cache
def get_settings() -> Settings:
    return Settings()
