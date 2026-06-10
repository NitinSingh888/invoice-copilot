"""Integration tests for POST /api/v1/chat."""
from __future__ import annotations

from collections.abc import Generator
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import Session, sessionmaker

import app.db.models  # noqa: F401 — populate metadata
from app.api.deps import get_db, get_llm
from app.clients.llm.mock_client import MockClient
from app.db.base import Base
from app.db.models.invoice import Invoice
from app.main import app
from tests.integration.api._seed import seed_clearable


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
        # Add a received invoice for process_batch tests
        s.add(
            Invoice(
                id="inv-recv-chat",
                status="received",
                vendor="Acme Corp",
                amount=Decimal("9800"),
                invoice_number="RECV-CHAT-1",
                po_number="PO-1",
            )
        )
        # Add an escalated invoice for approve tests — ID must match INV-\d+ for MockClient
        s.add(
            Invoice(
                id="INV-9002",
                status="needs",
                verdict="ESCALATE",
                vendor="Acme Corp",
                amount=Decimal("11300"),
                invoice_number="ESC-CHAT-1",
            )
        )
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
# process_batch intent
# ---------------------------------------------------------------------------


def test_chat_process_batch_intent(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/chat",
        json={"message": "process today's invoices"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "process_batch"
    assert data["result"] is not None
    assert "queued" in data["result"]
    assert "needs" in data["result"]
    assert "blocked" in data["result"]


def test_chat_process_batch_counts_are_numeric(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/chat",
        json={"message": "go ahead and run the batch"},
    )
    assert resp.status_code == 200
    result = resp.json()["result"]
    assert isinstance(result["queued"], int)
    assert isinstance(result["needs"], int)


# ---------------------------------------------------------------------------
# explain intent
# ---------------------------------------------------------------------------


def test_chat_explain_returns_trail(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/chat",
        json={"message": "why did you escalate INV-4495?"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "explain"
    assert data["result"] is not None
    assert data["result"]["invoice_id"] == "INV-4495"


# ---------------------------------------------------------------------------
# approve intent
# ---------------------------------------------------------------------------


def test_chat_approve_transitions_invoice(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/chat",
        json={"message": "approve INV-9002"},
        headers={"X-Role": "priya"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "approve"
    assert data["result"] is not None
    assert data["result"]["invoice_id"] == "INV-9002"
    assert data["result"]["action"] == "approve"


# ---------------------------------------------------------------------------
# smalltalk intent
# ---------------------------------------------------------------------------


def test_chat_smalltalk_has_reply(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/chat",
        json={"message": "hello"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "smalltalk"
    assert len(data["reply"]) > 0
    assert data["result"] is None


# ---------------------------------------------------------------------------
# history is accepted
# ---------------------------------------------------------------------------


def test_chat_with_history(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/chat",
        json={
            "message": "process invoices",
            "history": [{"role": "assistant", "content": "How can I help?"}],
        },
    )
    assert resp.status_code == 200
    assert resp.json()["intent"] == "process_batch"
