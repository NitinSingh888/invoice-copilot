from __future__ import annotations

from sqlalchemy import inspect
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.db.session import get_session, init_db


def test_init_db_creates_tables(_engine: Engine) -> None:
    """init_db should create all expected tables (using the test engine)."""
    # Drop + recreate so we're testing init_db itself
    from app.db.base import Base

    Base.metadata.drop_all(_engine)
    init_db(_engine)
    table_names = inspect(_engine).get_table_names()
    for expected in ("invoices", "audit_events", "vendors", "purchase_orders"):
        assert expected in table_names, f"Table '{expected}' not found after init_db"


def test_get_session_yields_session() -> None:
    """get_session() should yield a Session instance and close cleanly."""
    gen = get_session()
    session = next(gen)
    assert isinstance(session, Session)
    try:
        next(gen)
    except StopIteration:
        pass
