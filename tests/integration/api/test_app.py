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
# Static serving — GET / → index.html
# ---------------------------------------------------------------------------


def test_static_index_html(client: TestClient) -> None:
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]


# ---------------------------------------------------------------------------
# E2E smoke — full multi-router round-trip
# ---------------------------------------------------------------------------

CLEAR_PAYLOAD = {
    "vendor": "Acme Corp",
    "amount": "9800",
    "po_number": "PO-1",
    "invoice_number": "E2E-1",
    "confidence": "HIGH",
}


def test_e2e_invoice_approve_audit(client: TestClient) -> None:
    # 1. POST invoice — auto-clear
    post_resp = client.post("/api/v1/invoices", json=CLEAR_PAYLOAD)
    assert post_resp.status_code == 201
    invoice_id = post_resp.json()["invoice_id"]

    # 2. GET invoice by id
    get_resp = client.get(f"/api/v1/invoices/{invoice_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == invoice_id

    # 3. POST action — approve
    action_resp = client.post(
        f"/api/v1/invoices/{invoice_id}/action",
        json={"action": "approve"},
    )
    assert action_resp.status_code == 200

    # 4. GET audit trail — non-empty and chain verified
    audit_resp = client.get(f"/api/v1/audit/{invoice_id}")
    assert audit_resp.status_code == 200
    data = audit_resp.json()
    assert isinstance(data["events"], list)
    assert len(data["events"]) > 0
    assert data["chain_verified"] is True
