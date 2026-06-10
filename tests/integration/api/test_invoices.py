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
from tests.integration.api._seed import seed_clearable


# ---------------------------------------------------------------------------
# Per-test in-memory DB (StaticPool so all connections share the same db)
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

    # Seed once before any requests
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
    with TestClient(app) as c:
        yield c

    app.dependency_overrides.pop(get_db, None)
    engine.dispose()


# ---------------------------------------------------------------------------
# Payloads
# ---------------------------------------------------------------------------

CLEAR_PAYLOAD = {
    "vendor": "Acme Corp",
    "amount": "9800",
    "po_number": "PO-1",
    "invoice_number": "A-1",
    "confidence": "HIGH",
}

ESCALATE_PAYLOAD = {
    "vendor": "Acme Corp",
    "amount": "11300",
    "po_number": "PO-1",
    "invoice_number": "B-1",
    "confidence": "HIGH",
}


# ---------------------------------------------------------------------------
# POST /invoices — auto-clear
# ---------------------------------------------------------------------------


def test_post_invoice_auto_clear(client: TestClient) -> None:
    resp = client.post("/api/v1/invoices", json=CLEAR_PAYLOAD)
    assert resp.status_code == 201
    data = resp.json()
    assert data["verdict"] == "AUTO_CLEAR"
    assert data["status"] == "queued"
    assert "invoice_id" in data


# ---------------------------------------------------------------------------
# POST /invoices — escalate over tolerance
# ---------------------------------------------------------------------------


def test_post_invoice_escalate(client: TestClient) -> None:
    resp = client.post("/api/v1/invoices", json=ESCALATE_PAYLOAD)
    assert resp.status_code == 201
    data = resp.json()
    assert data["verdict"] == "ESCALATE"
    assert data["status"] == "needs"


# ---------------------------------------------------------------------------
# GET /invoices — list non-empty
# ---------------------------------------------------------------------------


def test_list_invoices_non_empty(client: TestClient) -> None:
    client.post("/api/v1/invoices", json=CLEAR_PAYLOAD)
    resp = client.get("/api/v1/invoices")
    assert resp.status_code == 200
    items = resp.json()
    assert isinstance(items, list)
    assert len(items) > 0


# ---------------------------------------------------------------------------
# GET /invoices/{id} — found and not found
# ---------------------------------------------------------------------------


def test_get_invoice_by_id(client: TestClient) -> None:
    post = client.post("/api/v1/invoices", json=CLEAR_PAYLOAD)
    invoice_id = post.json()["invoice_id"]
    resp = client.get(f"/api/v1/invoices/{invoice_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == invoice_id


def test_get_invoice_missing(client: TestClient) -> None:
    resp = client.get("/api/v1/invoices/does-not-exist-xyz")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# POST /{id}/action — route escalated invoice
# ---------------------------------------------------------------------------


def test_invoice_action_route(client: TestClient) -> None:
    # Create an escalated invoice first
    post = client.post("/api/v1/invoices", json=ESCALATE_PAYLOAD)
    assert post.status_code == 201
    invoice_id = post.json()["invoice_id"]
    assert post.json()["verdict"] == "ESCALATE"

    # Route it as priya
    resp = client.post(
        f"/api/v1/invoices/{invoice_id}/action",
        json={"action": "route"},
        headers={"X-Role": "priya"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "routed"
