from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.db.models.invoice import Invoice
from app.domain.audit.chain import GENESIS
from app.repositories import audit_repo


def _add_invoice(db: Session, inv_id: str) -> None:
    """Helper: insert a minimal invoice row to satisfy the FK."""
    db.add(Invoice(id=inv_id, vendor="Test", amount=Decimal("100")))
    db.flush()


def test_chain_prev_hashes(db: Session) -> None:
    _add_invoice(db, "INV-1")
    _add_invoice(db, "INV-2")
    ev0 = audit_repo.append(db, invoice_id="INV-1", actor="sys", module="extractor", action="EXTRACT")
    ev1 = audit_repo.append(db, invoice_id="INV-1", actor="sys", module="matcher", action="MATCH")
    ev2 = audit_repo.append(db, invoice_id="INV-2", actor="human", module="review", action="APPROVE")

    assert ev0.prev_hash == GENESIS
    assert ev1.prev_hash == ev0.hash
    assert ev2.prev_hash == ev1.hash


def test_verify_intact_chain(db: Session) -> None:
    _add_invoice(db, "INV-1")
    _add_invoice(db, "INV-2")
    audit_repo.append(db, invoice_id="INV-1", actor="sys", module="extractor", action="EXTRACT")
    audit_repo.append(db, invoice_id="INV-1", actor="sys", module="matcher", action="MATCH")
    audit_repo.append(db, invoice_id="INV-2", actor="human", module="review", action="APPROVE")

    assert audit_repo.verify(db) is True


def test_list_for_invoice_filters(db: Session) -> None:
    _add_invoice(db, "INV-1")
    _add_invoice(db, "INV-2")
    audit_repo.append(db, invoice_id="INV-1", actor="sys", module="extractor", action="EXTRACT")
    audit_repo.append(db, invoice_id="INV-1", actor="sys", module="matcher", action="MATCH")
    audit_repo.append(db, invoice_id="INV-2", actor="human", module="review", action="APPROVE")

    results = audit_repo.list_for_invoice(db, "INV-1")
    assert len(results) == 2
    assert all(e.invoice_id == "INV-1" for e in results)
    # Ordered by seq asc
    assert results[0].seq < results[1].seq


def test_all_events_order(db: Session) -> None:
    # invoice_id is nullable — no parent needed
    audit_repo.append(db, actor="a", module="m", action="A1")
    audit_repo.append(db, actor="a", module="m", action="A2")
    evs = audit_repo.all_events(db)
    assert evs[0].seq < evs[1].seq


def test_verify_detects_tampered_field(db: Session) -> None:
    _add_invoice(db, "INV-1")
    _add_invoice(db, "INV-2")
    audit_repo.append(db, invoice_id="INV-1", actor="sys", module="extractor", action="EXTRACT")
    audit_repo.append(db, invoice_id="INV-1", actor="sys", module="matcher", action="MATCH")
    audit_repo.append(db, invoice_id="INV-2", actor="human", module="review", action="APPROVE")

    # Tamper: change the action on the second event
    ev = audit_repo.all_events(db)[1]
    ev.action = "HACKED"
    db.flush()

    assert audit_repo.verify(db) is False


def test_verify_empty_chain(db: Session) -> None:
    # Empty chain should be trivially valid
    assert audit_repo.verify(db) is True


def test_append_with_inputs_outputs(db: Session) -> None:
    _add_invoice(db, "INV-10")
    ev = audit_repo.append(
        db,
        invoice_id="INV-10",
        actor="sys",
        module="matcher",
        action="MATCH",
        inputs={"po_number": "PO-99"},
        outputs={"verdict": "ok"},
        rationale="exact match",
        model_meta={"model": "gpt-4"},
    )
    assert ev.inputs == {"po_number": "PO-99"}
    assert ev.outputs == {"verdict": "ok"}
    assert ev.rationale == "exact match"
    assert ev.model_meta == {"model": "gpt-4"}
    assert audit_repo.verify(db) is True


def test_verify_detects_tampered_prev_hash(db: Session) -> None:
    _add_invoice(db, "INV-1")
    audit_repo.append(db, invoice_id="INV-1", actor="sys", module="m", action="A")
    audit_repo.append(db, invoice_id="INV-1", actor="sys", module="m", action="B")

    # Tamper the stored prev_hash on the second event
    evs = audit_repo.all_events(db)
    evs[1].prev_hash = "0" * 64  # reset to GENESIS — wrong
    db.flush()

    assert audit_repo.verify(db) is False
