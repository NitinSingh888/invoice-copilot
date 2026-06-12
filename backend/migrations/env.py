from __future__ import annotations

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# ---------------------------------------------------------------------------
# Alembic config object
# ---------------------------------------------------------------------------
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ---------------------------------------------------------------------------
# Wire up the application metadata so autogenerate sees every table.
# All models must be imported here (importing the package __init__ is enough
# because it re-exports every model class).
# ---------------------------------------------------------------------------
import app.db.models  # noqa: F401,E402 — registers all ORM classes with Base.metadata
from app.db.base import Base  # noqa: E402

target_metadata = Base.metadata

# ---------------------------------------------------------------------------
# Override the URL from the application settings so there is a single source
# of truth (no copy-pasting credentials into alembic.ini).
# ---------------------------------------------------------------------------
from app.core.config import get_settings  # noqa: E402

config.set_main_option("sqlalchemy.url", get_settings().database_url)


# ---------------------------------------------------------------------------
# Migration helpers
# ---------------------------------------------------------------------------


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (generate SQL only, no live connection)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (live Postgres connection)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
