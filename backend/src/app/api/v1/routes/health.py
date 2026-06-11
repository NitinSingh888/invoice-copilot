from __future__ import annotations

from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter()


@router.get("/health")
def health() -> dict[str, object]:
    provider = get_settings().llm_provider
    return {"status": "ok", "provider": provider, "live": provider != "mock"}
