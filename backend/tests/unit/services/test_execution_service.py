from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.db.models.invoice import Invoice
from app.repositories import invoice_repo
from app.services import audit_service
from app.services.execution_service import execute


def _seed_invoice(db: Session, inv_id: str = "inv-1", status: str = "received") -> Invoice:
    return invoice_repo.add(
        db,
        Invoice(
            id=inv_id,
            status=status,
            vendor="Acme Corp",
            amount=Decimal("1000.00"),
            invoice_number="INV-001",
        ),
    )


def test_approve_transitions_to_queued(db: Session) -> None:
    _seed_invoice(db, "inv-1", "received")
    result = execute(db, "inv-1", "approve", actor="maya")
    assert result.status == "queued"


def test_approve_creates_executed_queued_payment_event(db: Session) -> None:
    _seed_invoice(db, "inv-1", "received")
    execute(db, "inv-1", "approve", actor="maya")
    events = audit_service.trail(db, "inv-1")
    actions = [e.action for e in events]
    assert "executed:queued_payment" in actions


def test_approve_idempotent_creates_noop_event(db: Session) -> None:
    _seed_invoice(db, "inv-1", "received")

    # First call — state-changing
    execute(db, "inv-1", "approve", actor="maya")

    # Second call — idempotent
    result = execute(db, "inv-1", "approve", actor="maya")
    assert result.status == "queued"

    events = audit_service.trail(db, "inv-1")
    state_changing = [e for e in events if e.action == "executed:queued_payment"]
    noop_events = [e for e in events if e.action == "execute:noop"]
    assert len(state_changing) == 1
    assert len(noop_events) == 1


def test_route_transitions_to_routed(db: Session) -> None:
    _seed_invoice(db, "inv-2", "received")
    result = execute(db, "inv-2", "route", actor="priya")
    assert result.status == "routed"


def test_route_creates_executed_routed_event(db: Session) -> None:
    _seed_invoice(db, "inv-2", "received")
    execute(db, "inv-2", "route", actor="priya")
    events = audit_service.trail(db, "inv-2")
    actions = [e.action for e in events]
    assert "executed:routed" in actions


def test_hold_transitions_to_held(db: Session) -> None:
    _seed_invoice(db, "inv-3", "received")
    result = execute(db, "inv-3", "hold", actor="admin")
    assert result.status == "held"


def test_hold_creates_executed_held_event(db: Session) -> None:
    _seed_invoice(db, "inv-3", "received")
    execute(db, "inv-3", "hold", actor="admin")
    events = audit_service.trail(db, "inv-3")
    actions = [e.action for e in events]
    assert "executed:held" in actions


def test_execute_raises_on_unknown_invoice(db: Session) -> None:
    with pytest.raises(ValueError, match="not found"):
        execute(db, "ghost", "approve", actor="maya")


def test_edit_transitions_to_queued(db: Session) -> None:
    _seed_invoice(db, "inv-4", "received")
    result = execute(db, "inv-4", "edit", actor="editor")
    assert result.status == "queued"
