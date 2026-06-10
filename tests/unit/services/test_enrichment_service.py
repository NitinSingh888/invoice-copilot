from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.db.models.invoice import Invoice
from app.db.models.purchase_order import PurchaseOrder
from app.db.models.vendor import Vendor
from app.domain.policy.matching import InvoiceData
from app.repositories import invoice_repo, po_repo, vendor_repo
from app.services.enrichment_service import enrich


def _invoice_data(
    invoice_id: str = "inv-1",
    vendor: str = "Acme Corp",
    amount: str = "1000.00",
    po_number: str | None = "PO-100",
    invoice_number: str = "INV-001",
) -> InvoiceData:
    return InvoiceData(
        invoice_id=invoice_id,
        vendor=vendor,
        amount=Decimal(amount),
        po_number=po_number,
        invoice_number=invoice_number,
    )


def test_unknown_vendor_status(db: Session) -> None:
    inv = _invoice_data(vendor="UnknownCorp", po_number=None)
    result = enrich(db, inv)
    assert result.vendor_status == "new"


def test_approved_vendor_status(db: Session) -> None:
    vendor_repo.add(db, Vendor(id="v1", canonical_name="Acme Corp", status="approved"))
    inv = _invoice_data(vendor="Acme Corp", po_number=None)
    result = enrich(db, inv)
    assert result.vendor_status == "approved"


def test_matching_po_populated(db: Session) -> None:
    po_repo.add(
        db,
        PurchaseOrder(
            id="po-1",
            po_number="PO-100",
            vendor="Acme Corp",
            amount=Decimal("1000.00"),
        ),
    )
    inv = _invoice_data(po_number="PO-100")
    result = enrich(db, inv)
    assert result.po_match.po is not None
    assert result.po_match.po.po_number == "PO-100"


def test_no_po_number_gives_empty_match(db: Session) -> None:
    inv = _invoice_data(po_number=None)
    result = enrich(db, inv)
    assert result.po_match.po is None
    assert result.po_match.ambiguous is False


def test_cleared_exact_appears(db: Session) -> None:
    invoice_repo.add(
        db,
        Invoice(
            id="old-inv",
            status="cleared",
            vendor="Acme Corp",
            amount=Decimal("1000.00"),
            invoice_number="INV-001",
        ),
    )
    inv = _invoice_data(vendor="Acme Corp", invoice_number="INV-001")
    result = enrich(db, inv)
    assert any(d.invoice_id == "old-inv" for d in result.cleared_exact)


def test_cleared_exact_different_invoice_number_not_included(db: Session) -> None:
    invoice_repo.add(
        db,
        Invoice(
            id="other-inv",
            status="cleared",
            vendor="Acme Corp",
            amount=Decimal("1000.00"),
            invoice_number="INV-999",
        ),
    )
    inv = _invoice_data(vendor="Acme Corp", invoice_number="INV-001")
    result = enrich(db, inv)
    assert result.cleared_exact == []


def test_recent_same_amount_within_window(db: Session) -> None:
    invoice_repo.add(
        db,
        Invoice(
            id="recent-inv",
            status="received",
            vendor="Acme Corp",
            amount=Decimal("1000.00"),
            invoice_number="INV-002",
        ),
    )
    inv = _invoice_data(vendor="Acme Corp", amount="1000.00", invoice_number="INV-001")
    result = enrich(db, inv)
    assert any(d.invoice_id == "recent-inv" for d in result.recent_same_amount)
