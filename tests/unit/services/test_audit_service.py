from __future__ import annotations

from sqlalchemy.orm import Session

from app.services import audit_service


def test_record_returns_audit_event(db: Session) -> None:
    event = audit_service.record(
        db,
        invoice_id="inv-1",
        actor="maya",
        module="test",
        action="test_action",
        rationale="testing",
    )
    assert event.invoice_id == "inv-1"
    assert event.actor == "maya"
    assert event.action == "test_action"
    assert event.hash != ""


def test_trail_returns_events_for_invoice(db: Session) -> None:
    audit_service.record(db, invoice_id="inv-1", actor="maya", module="m", action="a1")
    audit_service.record(db, invoice_id="inv-2", actor="bob", module="m", action="a2")
    audit_service.record(db, invoice_id="inv-1", actor="maya", module="m", action="a3")

    trail = audit_service.trail(db, "inv-1")
    assert len(trail) == 2
    assert all(e.invoice_id == "inv-1" for e in trail)
    assert [e.action for e in trail] == ["a1", "a3"]


def test_verify_valid_chain(db: Session) -> None:
    audit_service.record(db, invoice_id="inv-1", actor="sys", module="m", action="first")
    audit_service.record(db, invoice_id="inv-1", actor="sys", module="m", action="second")
    assert audit_service.verify(db) is True


def test_verify_empty_chain(db: Session) -> None:
    assert audit_service.verify(db) is True
