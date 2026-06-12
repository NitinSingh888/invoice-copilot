from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.db.models import (
    AuditEvent,
    Correction,
    Invoice,
    PurchaseOrder,
    Rule,
    Vendor,
)


def test_vendor_roundtrip(db: Session) -> None:
    v = Vendor(id="v1", canonical_name="ACME Corp", aliases=["ACME"])
    db.add(v)
    db.flush()
    result = db.get(Vendor, "v1")
    assert result is not None
    assert result.canonical_name == "ACME Corp"
    assert result.aliases == ["ACME"]
    assert result.status == "new"
    assert result.default_approver is None


def test_purchase_order_roundtrip(db: Session) -> None:
    po = PurchaseOrder(
        id="po1",
        po_number="PO-001",
        vendor="ACME",
        amount=Decimal("10000.00"),
        currency="USD",
    )
    db.add(po)
    db.flush()
    result = db.get(PurchaseOrder, "po1")
    assert result is not None
    assert result.amount == Decimal("10000.00")
    assert result.status == "open"
    assert result.currency == "USD"


def test_invoice_roundtrip(db: Session) -> None:
    inv = Invoice(
        id="inv1",
        vendor="ACME",
        amount=Decimal("9500.00"),
        po_number="PO-001",
    )
    db.add(inv)
    db.flush()
    result = db.get(Invoice, "inv1")
    assert result is not None
    assert result.amount == Decimal("9500.00")
    assert result.status == "received"
    assert isinstance(result.created_at, datetime)


def test_rule_roundtrip(db: Session) -> None:
    r = Rule(
        id="rule1",
        vendor="ACME",
        route="auto",
        source_correction_ids=["c1", "c2"],
    )
    db.add(r)
    db.flush()
    result = db.get(Rule, "rule1")
    assert result is not None
    assert result.status == "active"
    assert result.source_correction_ids == ["c1", "c2"]


def test_correction_roundtrip(db: Session) -> None:
    # FK: correction.invoice_id → invoices.id — parent must exist first.
    db.add(Invoice(id="inv1", vendor="ACME", amount=Decimal("9500.00")))
    db.flush()

    c = Correction(
        id="corr1",
        invoice_id="inv1",
        vendor="ACME",
        finding_code="OVER_TOLERANCE",
        user_action="approve",
        over_pct=Decimal("0.0500"),
    )
    db.add(c)
    db.flush()
    result = db.get(Correction, "corr1")
    assert result is not None
    assert result.over_pct == Decimal("0.0500")
    assert isinstance(result.created_at, datetime)


def test_audit_event_roundtrip(db: Session) -> None:
    # FK: audit_event.invoice_id → invoices.id — parent must exist first.
    db.add(Invoice(id="inv1", vendor="ACME", amount=Decimal("9500.00")))
    db.flush()

    ae = AuditEvent(
        invoice_id="inv1",
        actor="system",
        module="decision",
        action="AUTO_CLEAR",
        inputs={"k": "v"},
        outputs={"verdict": "AUTO_CLEAR"},
        prev_hash="0" * 64,
        hash="abc123",
    )
    db.add(ae)
    db.flush()
    from sqlalchemy import select

    result = db.execute(select(AuditEvent)).scalars().first()
    assert result is not None
    assert result.inputs == {"k": "v"}
    assert result.outputs == {"verdict": "AUTO_CLEAR"}
    assert isinstance(result.ts, datetime)
