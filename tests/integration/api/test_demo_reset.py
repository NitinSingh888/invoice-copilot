"""Integration tests for POST /api/v1/demo/reset."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import Session, sessionmaker

import app.db.models  # noqa: F401 — populate metadata
from app.api.deps import get_db
from app.db.base import Base
from app.main import app


# ---------------------------------------------------------------------------
# Per-test in-memory DB (no pre-seed — demo/reset provides the data)
# ---------------------------------------------------------------------------


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, expire_on_commit=False)

    def override_get_db() -> Generator[Session, None, None]:
        s: Session = TestingSession()
        try:
            yield s
            s.commit()
        finally:
            s.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c

    app.dependency_overrides.pop(get_db, None)
    engine.dispose()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_demo_reset_returns_200(client: TestClient) -> None:
    resp = client.post("/api/v1/demo/reset")
    assert resp.status_code == 200


def test_demo_reset_returns_reseeded_status(client: TestClient) -> None:
    resp = client.post("/api/v1/demo/reset")
    data = resp.json()
    assert data["status"] == "reseeded"


def test_demo_reset_received_count_positive(client: TestClient) -> None:
    resp = client.post("/api/v1/demo/reset")
    data = resp.json()
    assert data["received"] > 0


def test_demo_reset_then_list_invoices_non_empty(client: TestClient) -> None:
    client.post("/api/v1/demo/reset")
    resp = client.get("/api/v1/invoices")
    assert resp.status_code == 200
    items = resp.json()
    assert isinstance(items, list)
    assert len(items) > 0


def test_demo_reset_idempotent_second_call_reseeds(client: TestClient) -> None:
    """Calling reset twice should always return the full batch (force=True)."""
    r1 = client.post("/api/v1/demo/reset")
    r2 = client.post("/api/v1/demo/reset")
    assert r1.json()["received"] == r2.json()["received"]


def test_demo_reset_clears_then_reseeds(client: TestClient) -> None:
    """After first reset, a second reset re-seeds from scratch."""
    client.post("/api/v1/demo/reset")
    # Simulate some work — just check invoices were loaded
    after_first = client.get("/api/v1/invoices").json()
    first_count = len(after_first)
    assert first_count > 0

    # Second reset
    client.post("/api/v1/demo/reset")
    after_second = client.get("/api/v1/invoices").json()
    # After a force-reseed the received batch count is the same
    received_after = [i for i in after_second if i["status"] == "received"]
    assert len(received_after) > 0
