"""Integration tests for POST /api/v1/chat."""
from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models.invoice import Invoice


@pytest.fixture()
def chat_client(seeded_client: TestClient, db: Session) -> TestClient:
    """seeded_client with extra invoices for chat tests."""
    # Add a received invoice for process_batch tests
    db.add(
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
    db.add(
        Invoice(
            id="INV-9002",
            status="needs",
            verdict="ESCALATE",
            vendor="Acme Corp",
            amount=Decimal("11300"),
            invoice_number="ESC-CHAT-1",
        )
    )
    db.commit()
    return seeded_client


# ---------------------------------------------------------------------------
# process_batch intent
# ---------------------------------------------------------------------------


def test_chat_process_batch_intent(chat_client: TestClient) -> None:
    resp = chat_client.post(
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


def test_chat_process_batch_counts_are_numeric(chat_client: TestClient) -> None:
    resp = chat_client.post(
        "/api/v1/chat",
        json={"message": "go ahead and run the batch"},
    )
    assert resp.status_code == 200
    result = resp.json()["result"]
    assert isinstance(result["queued"], int)
    assert isinstance(result["needs"], int)


# ---------------------------------------------------------------------------
# explain intent → "why" questions now map to smalltalk
# ---------------------------------------------------------------------------


def test_chat_why_returns_smalltalk(chat_client: TestClient) -> None:
    resp = chat_client.post(
        "/api/v1/chat",
        json={"message": "why did you escalate INV-4495?"},
    )
    assert resp.status_code == 200
    data = resp.json()
    # "why" has no process/review/approve action keyword → smalltalk
    assert data["intent"] == "smalltalk"


# ---------------------------------------------------------------------------
# approve → now returns bulk_confirm (no immediate execution)
# ---------------------------------------------------------------------------


def test_chat_approve_returns_bulk_confirm(chat_client: TestClient) -> None:
    resp = chat_client.post(
        "/api/v1/chat",
        json={"message": "approve INV-9002"},
        headers={"X-Role": "priya"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "bulk_confirm"
    assert data["result"] is not None
    assert data["result"]["bulk"]["action"] == "approve"


# ---------------------------------------------------------------------------
# smalltalk intent
# ---------------------------------------------------------------------------


def test_chat_smalltalk_has_reply(chat_client: TestClient) -> None:
    resp = chat_client.post(
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


def test_chat_with_history(chat_client: TestClient) -> None:
    resp = chat_client.post(
        "/api/v1/chat",
        json={
            "message": "process invoices",
            "history": [{"role": "assistant", "content": "How can I help?"}],
        },
    )
    assert resp.status_code == 200
    assert resp.json()["intent"] == "process_batch"
