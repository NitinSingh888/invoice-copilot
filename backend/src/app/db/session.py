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

    Called once at app boot (lifespan). Safe to call on an already-up-to-date
    DB (no-op) or a fresh DB (creates all tables).

    The ``migrations/`` directory and ``alembic.ini`` live next to the project
    root, but the *code* may run either from a source checkout (dev /
    docker-compose, where ``__file__`` is ``<root>/src/app/db/session.py``) or
    from an installed package (production image, where ``pip install .`` puts
    the code under ``site-packages`` while the Dockerfile copies ``migrations/``
    + ``alembic.ini`` to the WORKDIR). So we resolve the root by checking the
    candidate locations and using the first one that actually contains
    ``migrations/`` — never a fixed ``parents[N]`` guess.
    """
    import os
    from pathlib import Path

    import alembic.command
    import alembic.config

    candidates = [
        Path(__file__).resolve().parents[3],  # source layout: <root>
        Path.cwd(),  # container WORKDIR (e.g. /app) where the Dockerfile copies them
    ]
    env_root = os.environ.get("IC_PROJECT_ROOT")
    if env_root:
        candidates.insert(0, Path(env_root))

    root = next((c for c in candidates if (c / "migrations").is_dir()), None)
    if root is None:
        raise RuntimeError(
            "Alembic migrations directory not found in any of: "
            + ", ".join(str(c) for c in candidates)
        )

    ini_path = root / "alembic.ini"
    cfg = alembic.config.Config(str(ini_path) if ini_path.exists() else None)
    # Set explicitly so neither a missing ini nor a misread %(here)s can break boot.
    cfg.set_main_option("script_location", str(root / "migrations"))
    # Override URL so we always use the app settings, not the ini file value.
    cfg.set_main_option("sqlalchemy.url", _settings.database_url)
    alembic.command.upgrade(cfg, "head")
