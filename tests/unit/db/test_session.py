from __future__ import annotations

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.db.session import get_session


def test_select_one() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with Session(engine) as s:
        result = s.execute(text("SELECT 1")).scalar()
    assert result == 1


def test_get_session_yields_session() -> None:
    gen = get_session()
    session = next(gen)
    assert isinstance(session, Session)
    try:
        next(gen)
    except StopIteration:
        pass
