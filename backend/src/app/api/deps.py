from __future__ import annotations

from collections.abc import Iterator

from fastapi import Header
from sqlalchemy.orm import Session

from app.clients.llm.base import LLMClient
from app.clients.llm.factory import build_llm_client
from app.core.config import get_settings
from app.core.security import current_role
from app.db.session import SessionLocal

# Module-level cache — one client per process lifetime.
_llm_client: LLMClient | None = None


def get_llm() -> LLMClient:
    global _llm_client
    if _llm_client is None:
        _llm_client = build_llm_client(get_settings())
    return _llm_client


def get_db() -> Iterator[Session]:
    s: Session = SessionLocal()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


def get_role(x_role: str | None = Header(default=None)) -> str:
    return current_role(x_role)
