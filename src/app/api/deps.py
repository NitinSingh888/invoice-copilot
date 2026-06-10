from __future__ import annotations

from collections.abc import Iterator

from fastapi import Header
from sqlalchemy.orm import Session

from app.core.security import current_role
from app.db.session import SessionLocal


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
