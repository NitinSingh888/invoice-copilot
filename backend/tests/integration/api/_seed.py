from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models.invoice import Invoice
from app.db.models.organization import Organization
from app.db.models.purchase_order import PurchaseOrder
from app.db.models.vendor import Vendor
from app.repositories import invoice_repo, po_repo, vendor_repo

# Default test org (matches conftest.TEST_ORG_ID)
_DEFAULT_ORG_ID = "org-test0001"


def seed_clearable(s: Session, org_id: str = _DEFAULT_ORG_ID) -> None:
    """Seed an approved Vendor, a matching PO, and enough cleared invoices to
    satisfy the cold-start check so that well-formed invoices auto-clear."""
    settings = get_settings()

    # Ensure the org row exists. These fixtures exercise the auto-clear *envelope*
    # (approved vendor + PO match + cold-start), not the per-org amount cap, so
    # set a high threshold and let amounts up to ~$10k auto-clear.
    org = s.get(Organization, org_id)
    if org is None:
        org = Organization(id=org_id, name=f"Test Org {org_id}")
        s.add(org)
        s.flush()
    org.auto_approve_threshold = Decimal("1000000")
    s.flush()

    vendor = Vendor(id=f"v-acme-{org_id}", canonical_name="Acme Corp", status="approved", org_id=org_id)
    vendor_repo.add(s, vendor)

    po = PurchaseOrder(
        id=f"po-acme-1-{org_id}",
        po_number="PO-1",
        vendor="Acme Corp",
        amount=Decimal("10000"),
        org_id=org_id,
    )
    po_repo.add(s, po)

    for i in range(settings.cold_start_n):
        invoice_repo.add(
            s,
            Invoice(
                id=f"hist-acme-{i}-{org_id}",
                status="cleared",
                vendor="Acme Corp",
                amount=Decimal("1000.00"),
                invoice_number=f"HIST-ACME-{i}",
                org_id=org_id,
            ),
        )
    s.flush()


def seed_without_cold_start(s: Session, org_id: str = _DEFAULT_ORG_ID) -> None:
    """Seed just the vendor and PO, with no historical cleared invoices."""
    if s.get(Organization, org_id) is None:
        s.add(Organization(id=org_id, name=f"Test Org {org_id}"))
        s.flush()

    vendor = Vendor(id=f"v-acme-{org_id}", canonical_name="Acme Corp", status="approved", org_id=org_id)
    vendor_repo.add(s, vendor)

    po = PurchaseOrder(
        id=f"po-acme-1-{org_id}",
        po_number="PO-1",
        vendor="Acme Corp",
        amount=Decimal("10000"),
        org_id=org_id,
    )
    po_repo.add(s, po)
    s.flush()
