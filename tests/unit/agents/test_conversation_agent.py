"""Unit tests for conversation_agent — MockClient + in-memory DB."""
from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import Session, sessionmaker

import app.db.models  # noqa: F401 — populate metadata
from app.agents import conversation_agent
from app.clients.llm.mock_client import MockClient
from app.db.base import Base
from app.db.models.invoice import Invoice
from app.schemas.chat import ChatMessageIn
from tests.integration.api._seed import seed_clearable


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db() -> Session:  # type: ignore[return]
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
    with TestingSession() as s:
        yield s


@pytest.fixture()
def client() -> MockClient:
    return MockClient()


# ---------------------------------------------------------------------------
# process_batch intent
# ---------------------------------------------------------------------------


def test_process_batch_returns_counts(db: Session, client: MockClient) -> None:
    # Seed a "received" invoice so the batch has something to process
    db.add(
        Invoice(
            id="inv-recv-1",
            status="received",
            vendor="Acme Corp",
            amount=Decimal("9800"),
            invoice_number="RECV-1",
            po_number="PO-1",
        )
    )
    db.flush()

    _, intent, result = conversation_agent.handle(
        client,
        db,
        message="process today's invoices",
        history=[],
        role="maya",
    )
    assert intent == "process_batch"
    assert result is not None
    assert "queued" in result
    assert "needs" in result
    assert "blocked" in result


def test_process_batch_counts_are_ints(db: Session, client: MockClient) -> None:
    _, _, result = conversation_agent.handle(
        client,
        db,
        message="run the batch now",
        history=[],
        role="maya",
    )
    assert result is not None
    assert isinstance(result["queued"], int)
    assert isinstance(result["needs"], int)
    assert isinstance(result["blocked"], int)


# ---------------------------------------------------------------------------
# explain intent
# ---------------------------------------------------------------------------


def test_explain_returns_trail_for_known_invoice(db: Session, client: MockClient) -> None:
    # First process an invoice so there's an audit trail
    from app.services import pipeline_service
    from app.domain.policy.matching import InvoiceData

    pipeline_service.process_invoice(
        db,
        InvoiceData(
            invoice_id="INV-4495",
            vendor="Acme Corp",
            amount=Decimal("11500"),
            po_number="PO-1",
            invoice_number="INV-4495",
        ),
        "HIGH",
    )
    db.flush()

    _, intent, result = conversation_agent.handle(
        client,
        db,
        message="why did you escalate INV-4495?",
        history=[],
        role="priya",
    )
    assert intent == "explain"
    assert result is not None
    assert result["invoice_id"] == "INV-4495"
    assert "trail" in result


def test_explain_no_invoice_id_gives_none_result(db: Session, client: MockClient) -> None:
    # "why" intent but no INV-\d+ pattern in the message → args["invoice_id"] absent
    _, intent, result = conversation_agent.handle(
        client,
        db,
        message="why was that escalated?",
        history=[],
        role="priya",
    )
    assert intent == "explain"
    # No invoice_id in args → result stays None
    assert result is None


# ---------------------------------------------------------------------------
# approve intent
# ---------------------------------------------------------------------------


def test_approve_transitions_invoice(db: Session, client: MockClient) -> None:
    # Seed a "needs" (escalated) invoice — ID must match INV-\d+ for MockClient
    db.add(
        Invoice(
            id="INV-9001",
            status="needs",
            vendor="Acme Corp",
            amount=Decimal("11300"),
            invoice_number="ESC-1",
        )
    )
    db.flush()

    _, intent, result = conversation_agent.handle(
        client,
        db,
        message="approve INV-9001",
        history=[],
        role="priya",
    )
    assert intent == "approve"
    assert result is not None
    assert result["invoice_id"] == "INV-9001"
    assert result["action"] == "approve"

    # Verify the invoice status was changed
    from app.repositories import invoice_repo

    inv = invoice_repo.get(db, "INV-9001")
    assert inv is not None
    assert inv.status == "queued"


# ---------------------------------------------------------------------------
# smalltalk intent
# ---------------------------------------------------------------------------


def test_smalltalk_returns_none_result(db: Session, client: MockClient) -> None:
    _, intent, result = conversation_agent.handle(
        client,
        db,
        message="hello there",
        history=[],
        role="maya",
    )
    assert intent == "smalltalk"
    assert result is None


# ---------------------------------------------------------------------------
# history propagation
# ---------------------------------------------------------------------------


def test_history_is_passed_to_client(db: Session, client: MockClient) -> None:
    history = [ChatMessageIn(role="assistant", content="How can I help?")]
    _, intent, _ = conversation_agent.handle(
        client,
        db,
        message="process invoices",
        history=history,
        role="maya",
    )
    assert intent == "process_batch"
