from __future__ import annotations

import importlib
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db.base import Base

_settings = get_settings()
_connect_args = (
    {"check_same_thread": False} if "sqlite" in _settings.database_url else {}
)
engine = create_engine(_settings.database_url, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    session: Session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db(bind: object) -> None:
    importlib.import_module("app.db.models")
    Base.metadata.create_all(bind)  # type: ignore[arg-type]
