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

    # JWT / auth settings
    jwt_secret: str = "dev-insecure-change-me"
    jwt_expire_minutes: int = 1440
    jwt_algorithm: str = "HS256"

    # CORS — comma-separated allowed origins. In production the SPA is served
    # same-origin by this service, so CORS is effectively unused; these defaults
    # cover the local Vite dev server. Override with IC_CORS_ORIGINS if the
    # frontend is ever hosted on a separate domain.
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Root log level (DEBUG/INFO/WARNING/ERROR). INFO surfaces boot, migration,
    # and seed progress in the platform logs.
    log_level: str = "INFO"

    # Path to the directory containing sample invoice PDFs.
    # Set IC_SAMPLE_INVOICES_DIR to override (e.g. a Docker volume mount path).
    sample_invoices_dir: str = ""

    # S3 storage — set IC_S3_BUCKET to enable cloud storage for invoice docs.
    # When unset, falls back to local file storage.
    s3_bucket: str = ""
    s3_region: str = "us-east-1"
    s3_access_key: str = ""
    s3_secret_key: str = ""

    # LLM provider settings
    llm_provider: str = "mock"
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-4-6"
    openai_model: str = "gpt-4o"


@lru_cache
def get_settings() -> Settings:
    return Settings()
