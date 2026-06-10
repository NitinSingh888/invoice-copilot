"""Integration tests for POST /api/v1/invoices/upload."""
from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import Session, sessionmaker

import app.db.models  # noqa: F401 — populate metadata
from app.api.deps import get_db, get_llm
from app.clients.llm.mock_client import MockClient
from app.db.base import Base
from app.main import app
from tests.integration.api._seed import seed_clearable


PLAIN_FILE_FULL = (
    "inv.txt",
    b"vendor: Acme Corp\namount: 9800\npo: PO-1\ninvoice_number: A-1",
    "text/plain",
)

PLAIN_FILE_NO_AMOUNT = (
    "inv_low.txt",
    b"vendor: Acme Corp\npo: PO-1\ninvoice_number: B-1",
    "text/plain",
)


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, expire_on_commit=False)

    with TestingSession() as s:
        seed_clearable(s)
        s.commit()

    def override_get_db() -> Generator[Session, None, None]:
        s: Session = TestingSession()
        try:
            yield s
            s.commit()
        finally:
            s.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_llm] = lambda: MockClient()

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_llm, None)
    engine.dispose()


# ---------------------------------------------------------------------------
# HIGH-confidence upload → 201 with a verdict
# ---------------------------------------------------------------------------


def test_upload_full_invoice_returns_201(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/invoices/upload",
        files={"file": PLAIN_FILE_FULL},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "verdict" in data
    assert data["verdict"] in ("AUTO_CLEAR", "ESCALATE", "BLOCK")


def test_upload_full_invoice_has_invoice_id(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/invoices/upload",
        files={"file": PLAIN_FILE_FULL},
    )
    assert resp.status_code == 201
    assert resp.json()["invoice_id"].startswith("inv-")


# ---------------------------------------------------------------------------
# Missing amount → overall LOW → verdict ESCALATE
# ---------------------------------------------------------------------------


def test_upload_missing_amount_escalates(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/invoices/upload",
        files={"file": PLAIN_FILE_NO_AMOUNT},
    )
    assert resp.status_code == 201
    data = resp.json()
    # LOW confidence → guard must escalate (cannot AUTO_CLEAR with uncertain data)
    assert data["verdict"] == "ESCALATE"
