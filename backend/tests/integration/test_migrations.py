"""Smoke-test the Alembic migration chain against the dev Postgres.

These tests run against the **dev** database so they don't interfere with
the ``copilot_test`` DB that the ``_clean`` autouse fixture manages.  They
verify that:

  1. ``alembic upgrade head`` produces all expected tables / columns.
  2. ``alembic downgrade -1`` succeeds (migration 0002 → 0001) and the
     new columns / tables are removed.
  3. ``alembic upgrade head`` re-applies cleanly after a downgrade.

The dev DB is always left at ``head`` after each test (teardown).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect

# We always use the dev DB for migration tests so we don't disturb the test
# DB schema that the conftest _clean fixture expects to be at "head".
DEV_DATABASE_URL = "postgresql+psycopg://copilot:copilot@localhost:5432/copilot"

INI_PATH = str(Path(__file__).parents[2] / "alembic.ini")


def _alembic_cfg():  # type: ignore[return]
    """Return an Alembic Config pointed at the dev DB."""
    import alembic.config

    cfg = alembic.config.Config(INI_PATH)
    cfg.set_main_option("sqlalchemy.url", DEV_DATABASE_URL)
    return cfg


@pytest.fixture(scope="module")
def mig_engine():  # type: ignore[return]
    """SQLAlchemy engine for the dev DB, used only by migration tests."""
    engine = create_engine(DEV_DATABASE_URL)
    yield engine
    engine.dispose()


@pytest.fixture(autouse=True, scope="module")
def ensure_head_after_module(mig_engine):  # type: ignore[type-arg, return]
    """Always leave the dev DB at head after the migration test module finishes."""
    yield
    import alembic.command

    alembic.command.upgrade(_alembic_cfg(), "head")


def test_upgrade_head_creates_all_tables(mig_engine) -> None:  # type: ignore[type-arg]
    """After upgrade head, all 8 tables (incl. comments) must exist."""
    import alembic.command

    alembic.command.upgrade(_alembic_cfg(), "head")

    insp = inspect(mig_engine)
    tables = set(insp.get_table_names())
    expected = {
        "invoices", "purchase_orders", "vendors", "corrections",
        "rules", "audit_events", "users", "comments", "organizations", "llm_calls",
    }
    assert expected.issubset(tables), f"Missing tables: {expected - tables}"


def test_upgrade_head_new_invoice_columns(mig_engine) -> None:  # type: ignore[type-arg]
    """After upgrade head, invoices table has all new columns from migration 0002."""
    import alembic.command

    alembic.command.upgrade(_alembic_cfg(), "head")

    insp = inspect(mig_engine)
    cols = {c["name"] for c in insp.get_columns("invoices")}
    new_cols = {"decided_by", "decided_at", "decision_reason", "vendor_id", "is_deleted", "updated_at"}
    assert new_cols.issubset(cols), f"Missing columns: {new_cols - cols}"


def test_upgrade_head_check_constraints(mig_engine) -> None:  # type: ignore[type-arg]
    """After upgrade head, invoices has status and verdict check constraints."""
    import alembic.command

    alembic.command.upgrade(_alembic_cfg(), "head")

    insp = inspect(mig_engine)
    constraints = {c["name"] for c in insp.get_check_constraints("invoices")}
    assert "ck_invoices_status" in constraints
    assert "ck_invoices_verdict" in constraints


def test_downgrade_minus_one_removes_multitenancy_schema(mig_engine) -> None:  # type: ignore[type-arg]
    """Downgrading to 0002 removes the multitenancy (0003) + llm_calls (0004) schema."""
    import alembic.command

    alembic.command.upgrade(_alembic_cfg(), "head")
    # Downgrade to the pre-multitenancy revision explicitly (head has since moved
    # past 0003, so a relative "-1" would no longer land on it).
    alembic.command.downgrade(_alembic_cfg(), "0002")

    insp = inspect(mig_engine)
    tables = set(insp.get_table_names())
    # organizations + llm_calls tables should be removed
    assert "organizations" not in tables, "organizations table should be removed after downgrade"
    assert "llm_calls" not in tables, "llm_calls table should be removed after downgrade"

    # org_id should be removed from entity tables
    invoice_cols = {c["name"] for c in insp.get_columns("invoices")}
    assert "org_id" not in invoice_cols, "org_id should be removed from invoices after downgrade"

    # comments table should STILL be present (it was added in 0002, not reverted by 0003 downgrade)
    assert "comments" in tables, "comments table should remain after 0003 downgrade"

    # Restore to head so other tests (and the app) keep working.
    alembic.command.upgrade(_alembic_cfg(), "head")


def test_upgrade_head_after_downgrade_restores_schema(mig_engine) -> None:  # type: ignore[type-arg]
    """upgrade head after downgrade re-creates the full schema cleanly."""
    import alembic.command

    alembic.command.upgrade(_alembic_cfg(), "head")
    alembic.command.downgrade(_alembic_cfg(), "-1")
    alembic.command.upgrade(_alembic_cfg(), "head")

    insp = inspect(mig_engine)
    tables = set(insp.get_table_names())
    # All tables should be present after re-upgrade
    assert "comments" in tables
    assert "organizations" in tables
    cols = {c["name"] for c in insp.get_columns("invoices")}
    assert "is_deleted" in cols
    assert "updated_at" in cols
    assert "org_id" in cols
