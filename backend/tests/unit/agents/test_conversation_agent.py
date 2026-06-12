"""Unit tests for conversation_agent — MockClient + Postgres test DB."""
from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.agents import conversation_agent
from app.clients.llm.mock_client import MockClient
from app.db.models.invoice import Invoice
from app.schemas.chat import ChatMessageIn
from tests.integration.api._seed import seed_clearable


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def seeded_db(db: Session) -> Session:
    """db pre-seeded with clearable vendor/PO/history."""
    seed_clearable(db)
    db.commit()
    return db


@pytest.fixture()
def client() -> MockClient:
    return MockClient()


# ---------------------------------------------------------------------------
# process_batch intent
# ---------------------------------------------------------------------------


def test_process_batch_returns_counts(seeded_db: Session, client: MockClient) -> None:
    # Seed a "received" invoice so the batch has something to process
    seeded_db.add(
        Invoice(
            id="inv-recv-1",
            status="received",
            vendor="Acme Corp",
            amount=Decimal("9800"),
            invoice_number="RECV-1",
            po_number="PO-1",
        )
    )
    seeded_db.flush()

    _, intent, result = conversation_agent.handle(
        client,
        seeded_db,
        message="process today's invoices",
        history=[],
        role="maya",
    )
    assert intent == "process_batch"
    assert result is not None
    assert "queued" in result
    assert "needs" in result
    assert "blocked" in result


def test_process_batch_counts_are_ints(seeded_db: Session, client: MockClient) -> None:
    _, _, result = conversation_agent.handle(
        client,
        seeded_db,
        message="run the batch now",
        history=[],
        role="maya",
    )
    assert result is not None
    assert isinstance(result["queued"], int)
    assert isinstance(result["needs"], int)
    assert isinstance(result["blocked"], int)


# ---------------------------------------------------------------------------
# review_invoice intent — single invoice via entity reference
# ---------------------------------------------------------------------------


def test_review_invoice_by_id(
    seeded_db: Session, client: MockClient
) -> None:
    # Process an invoice so it exists with a verdict
    from app.domain.policy.matching import InvoiceData
    from app.services import pipeline_service

    pipeline_service.process_invoice(
        seeded_db,
        InvoiceData(
            invoice_id="INV-4495",
            vendor="Acme Corp",
            amount=Decimal("11500"),
            po_number="PO-1",
            invoice_number="INV-4495",
        ),
        "HIGH",
    )
    seeded_db.flush()

    _, intent, result = conversation_agent.handle(
        client,
        seeded_db,
        message="review invoice INV-4495",
        history=[],
        role="priya",
    )
    assert intent == "review_invoice"
    assert result is not None
    assert result["invoice"]["id"] == "INV-4495"


def test_unknown_message_returns_smalltalk(
    seeded_db: Session, client: MockClient
) -> None:
    _, intent, result = conversation_agent.handle(
        client,
        seeded_db,
        message="why was that escalated?",
        history=[],
        role="priya",
    )
    assert intent == "smalltalk"
    assert result is None


# ---------------------------------------------------------------------------
# approve intent → now returns bulk_confirm (no immediate execution)
# ---------------------------------------------------------------------------


def test_approve_returns_bulk_confirm(seeded_db: Session, client: MockClient) -> None:
    # Seed a "needs" (escalated) invoice
    seeded_db.add(
        Invoice(
            id="INV-9001",
            status="needs",
            vendor="Acme Corp",
            amount=Decimal("11300"),
            invoice_number="ESC-1",
        )
    )
    seeded_db.flush()

    _, intent, result = conversation_agent.handle(
        client,
        seeded_db,
        message="approve INV-9001",
        history=[],
        role="priya",
    )
    assert intent == "bulk_confirm"
    assert result is not None
    assert result["bulk"]["action"] == "approve"

    # Invoice must NOT be executed yet — status remains "needs"
    from app.repositories import invoice_repo

    inv = invoice_repo.get(seeded_db, "INV-9001")
    assert inv is not None
    assert inv.status == "needs"


# ---------------------------------------------------------------------------
# smalltalk intent
# ---------------------------------------------------------------------------


def test_smalltalk_returns_none_result(seeded_db: Session, client: MockClient) -> None:
    _, intent, result = conversation_agent.handle(
        client,
        seeded_db,
        message="hello there",
        history=[],
        role="maya",
    )
    assert intent == "smalltalk"
    assert result is None


# ---------------------------------------------------------------------------
# history propagation
# ---------------------------------------------------------------------------


def test_history_is_passed_to_client(seeded_db: Session, client: MockClient) -> None:
    history = [ChatMessageIn(role="assistant", content="How can I help?")]
    _, intent, _ = conversation_agent.handle(
        client,
        seeded_db,
        message="process invoices",
        history=history,
        role="maya",
    )
    assert intent == "process_batch"
