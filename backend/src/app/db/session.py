from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

_settings = get_settings()
engine = create_engine(_settings.database_url, pool_pre_ping=True)
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
    """Legacy helper used by tests and the old lifespan.

    Creates all tables from Base.metadata via ``create_all`` — useful in tests
    where Alembic is not involved and we want a fast schema setup.  Production
    code should use ``run_migrations`` instead.
    """
    import importlib

    from app.db.base import Base

    importlib.import_module("app.db.models")
    Base.metadata.create_all(bind)  # type: ignore[arg-type]


def run_migrations() -> None:
    """Run Alembic migrations to head programmatically.

    Called once at app boot (lifespan).  Uses a NullPool connection so the
    migration engine does not interfere with the application pool.  Safe to
    call on an already-up-to-date DB (no-op) or against a legacy DB that has
    no alembic_version row yet (auto-stamps).
    """
    from pathlib import Path

    import alembic.config
    import alembic.command

    # Locate the alembic.ini next to this package (backend root).
    # Works whether running from source or installed.
    ini_path = Path(__file__).parents[4] / "alembic.ini"

    cfg = alembic.config.Config(str(ini_path))
    # Override URL so we always use the app settings, not the ini file value.
    cfg.set_main_option("sqlalchemy.url", _settings.database_url)
    alembic.command.upgrade(cfg, "head")
