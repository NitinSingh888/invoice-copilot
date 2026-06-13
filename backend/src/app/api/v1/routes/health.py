from __future__ import annotations

from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import engine

router = APIRouter()


@router.get("/health")
def health() -> dict[str, object]:
    """Liveness probe — does not touch the database.

    Kept dependency-free so a serverless Postgres that has scaled to zero
    (cold start) never marks the service unhealthy during a deploy.
    """
    provider = get_settings().llm_provider
    return {"status": "ok", "provider": provider, "live": provider != "mock"}


@router.get("/health/ready")
def ready() -> dict[str, str]:
    """Readiness probe — verifies the database is reachable (SELECT 1).

    Returns 503 if the database cannot be reached, so monitoring can tell a
    live-but-not-ready process from a healthy one.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:  # pragma: no cover - exercised via integration
        raise HTTPException(status_code=503, detail="database unavailable") from exc
    return {"status": "ready", "db": "ok"}
