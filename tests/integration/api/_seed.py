from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models.invoice import Invoice
from app.db.models.purchase_order import PurchaseOrder
from app.db.models.vendor import Vendor
from app.repositories import invoice_repo, po_repo, vendor_repo


def seed_clearable(s: Session) -> None:
    """Seed an approved Vendor, a matching PO, and enough cleared invoices to
    satisfy the cold-start check so that well-formed invoices auto-clear."""
    settings = get_settings()

    vendor = Vendor(id="v-acme", canonical_name="Acme Corp", status="approved")
    vendor_repo.add(s, vendor)

    po = PurchaseOrder(
        id="po-acme-1",
        po_number="PO-1",
        vendor="Acme Corp",
        amount=Decimal("10000"),
    )
    po_repo.add(s, po)

    for i in range(settings.cold_start_n):
        invoice_repo.add(
            s,
            Invoice(
                id=f"hist-acme-{i}",
                status="cleared",
                vendor="Acme Corp",
                amount=Decimal("1000.00"),
                invoice_number=f"HIST-ACME-{i}",
            ),
        )
    s.flush()


def seed_without_cold_start(s: Session) -> None:
    """Seed just the vendor and PO, with no historical cleared invoices."""
    vendor = Vendor(id="v-acme", canonical_name="Acme Corp", status="approved")
    vendor_repo.add(s, vendor)

    po = PurchaseOrder(
        id="po-acme-1",
        po_number="PO-1",
        vendor="Acme Corp",
        amount=Decimal("10000"),
    )
    po_repo.add(s, po)
    s.flush()
