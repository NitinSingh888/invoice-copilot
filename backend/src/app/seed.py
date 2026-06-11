"""Demo seed dataset.

Mirrors web/data.js VENDORS and INVOICES so the live backend reproduces
the scripted demo batch:

  - ~10 routine invoices  → AUTO_CLEAR (queued)
  - 3 Acme escalations    → ESCALATE (needs)  [over-tolerance]
  - 1 Northwind           → ESCALATE (needs)  [over-tolerance + over cap]
  - 1 Cyberdyne           → ESCALATE (needs)  [unknown vendor, no PO]
  - 1 Stark               → BLOCK    (blocked) [exact duplicate]
"""

from __future__ import annotations

import logging
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models.audit_event import AuditEvent
from app.db.models.correction import Correction
from app.db.models.invoice import Invoice
from app.db.models.purchase_order import PurchaseOrder
from app.db.models.rule import Rule
from app.db.models.vendor import Vendor

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SEED_VENDORS — mirrors data.js VENDORS
# ---------------------------------------------------------------------------

SEED_VENDORS: list[Vendor] = [
    Vendor(
        id="v-acme",
        canonical_name="Acme Corp",
        aliases=[],
        status="approved",
        default_approver="Priya",
    ),
    Vendor(
        id="v-northwind",
        canonical_name="Northwind Logistics",
        aliases=[],
        status="approved",
        default_approver="Priya",
    ),
    # Cyberdyne is status "new" — the unknown-vendor / injection case
    Vendor(
        id="v-cyberdyne",
        canonical_name="Cyberdyne Systems",
        aliases=[],
        status="new",
        default_approver="Priya",
    ),
    Vendor(
        id="v-stark",
        canonical_name="Stark Industries",
        aliases=[],
        status="approved",
        default_approver="Priya",
    ),
    Vendor(
        id="v-globex",
        canonical_name="Globex Trading",
        aliases=[],
        status="approved",
        default_approver="Priya",
    ),
    Vendor(
        id="v-initech",
        canonical_name="Initech Software",
        aliases=[],
        status="approved",
        default_approver="Priya",
    ),
    Vendor(
        id="v-umbrella",
        canonical_name="Umbrella Supplies",
        aliases=[],
        status="approved",
        default_approver="Priya",
    ),
    Vendor(
        id="v-hooli",
        canonical_name="Hooli Cloud",
        aliases=[],
        status="approved",
        default_approver="Priya",
    ),
    Vendor(
        id="v-soylent",
        canonical_name="Soylent Foods",
        aliases=[],
        status="approved",
        default_approver="Priya",
    ),
    Vendor(
        id="v-meridian",
        canonical_name="Meridian Freight",
        aliases=[],
        status="approved",
        default_approver="Priya",
    ),
    Vendor(
        id="v-wayne",
        canonical_name="Wayne Office Supply",
        aliases=[],
        status="approved",
        default_approver="Priya",
    ),
]

# ---------------------------------------------------------------------------
# SEED_POS — one PO per invoice that references one.
# PO amount is set so the pipeline produces the intended outcome:
#   • routine queued  → PO amount == invoice amount (0% over → INFO → AUTO_CLEAR)
#   • escalations     → PO amount from data.js poAmount (over tolerance → ESCALATE)
#   • Cyberdyne       → no PO (po_number None on the invoice)
#   • Stark duplicate → PO exists but the HARD_STOP from duplicate fires first
# ---------------------------------------------------------------------------

SEED_POS: list[PurchaseOrder] = [
    # -- escalations --
    PurchaseOrder(
        id="po-northwind-22841",
        po_number="PO-22841",
        vendor="Northwind Logistics",
        amount=Decimal("10970"),   # 13% under INV-4471 amount of 12400
    ),
    PurchaseOrder(
        id="po-acme-22790",
        po_number="PO-22790",
        vendor="Acme Corp",
        amount=Decimal("7735"),    # 6% under INV-4483 amount of 8200
    ),
    PurchaseOrder(
        id="po-acme-22802",
        po_number="PO-22802",
        vendor="Acme Corp",
        amount=Decimal("5283"),    # ~6% under INV-4488 amount of 5600 (over tolerance)
    ),
    PurchaseOrder(
        id="po-acme-22815",
        po_number="PO-22815",
        vendor="Acme Corp",
        amount=Decimal("8551"),    # 7% under INV-4490 amount of 9150
    ),
    # -- blocked (Stark duplicate) --
    PurchaseOrder(
        id="po-stark-22760",
        po_number="PO-22760",
        vendor="Stark Industries",
        amount=Decimal("9900"),
    ),
    # -- routine auto-clear POs (amount == invoice amount) --
    PurchaseOrder(
        id="po-globex-22845",
        po_number="PO-22845",
        vendor="Globex Trading",
        amount=Decimal("2480"),
    ),
    PurchaseOrder(
        id="po-initech-22848",
        po_number="PO-22848",
        vendor="Initech Software",
        amount=Decimal("1990"),
    ),
    PurchaseOrder(
        id="po-hooli-22851",
        po_number="PO-22851",
        vendor="Hooli Cloud",
        amount=Decimal("3450"),
    ),
    PurchaseOrder(
        id="po-soylent-22853",
        po_number="PO-22853",
        vendor="Soylent Foods",
        amount=Decimal("870"),
    ),
    PurchaseOrder(
        id="po-meridian-22855",
        po_number="PO-22855",
        vendor="Meridian Freight",
        amount=Decimal("4120"),
    ),
    PurchaseOrder(
        id="po-wayne-22858",
        po_number="PO-22858",
        vendor="Wayne Office Supply",
        amount=Decimal("640"),
    ),
    PurchaseOrder(
        id="po-umbrella-22861",
        po_number="PO-22861",
        vendor="Umbrella Supplies",
        amount=Decimal("2870"),
    ),
    PurchaseOrder(
        id="po-globex-22863",
        po_number="PO-22863",
        vendor="Globex Trading",
        amount=Decimal("5310"),
    ),
    PurchaseOrder(
        id="po-hooli-22866",
        po_number="PO-22866",
        vendor="Hooli Cloud",
        amount=Decimal("1280"),
    ),
    PurchaseOrder(
        id="po-initech-22868",
        po_number="PO-22868",
        vendor="Initech Software",
        amount=Decimal("3990"),
    ),
]

# ---------------------------------------------------------------------------
# The received batch — mirrors data.js INVOICES
# ---------------------------------------------------------------------------

SEED_INVOICES: list[Invoice] = [
    # ---- escalations ----
    Invoice(
        id="INV-4471",
        invoice_number="INV-4471",
        status="received",
        vendor="Northwind Logistics",
        amount=Decimal("12400"),
        po_number="PO-22841",
        confidence="HIGH",
    ),
    Invoice(
        id="INV-4483",
        invoice_number="INV-4483",
        status="received",
        vendor="Acme Corp",
        amount=Decimal("8200"),
        po_number="PO-22790",
        confidence="HIGH",
    ),
    Invoice(
        id="INV-4488",
        invoice_number="INV-4488",
        status="received",
        vendor="Acme Corp",
        amount=Decimal("5600"),
        po_number="PO-22802",
        confidence="HIGH",
    ),
    Invoice(
        id="INV-4490",
        invoice_number="INV-4490",
        status="received",
        vendor="Acme Corp",
        amount=Decimal("9150"),
        po_number="PO-22815",
        confidence="HIGH",
    ),
    # ---- injection / unknown vendor ----
    Invoice(
        id="INV-4495",
        invoice_number="INV-4495",
        status="received",
        vendor="Cyberdyne Systems",
        amount=Decimal("7300"),
        po_number=None,           # No PO for Cyberdyne
        confidence="MED",
    ),
    # ---- exact duplicate (Stark) ----
    Invoice(
        id="INV-4502",
        invoice_number="INV-4502",
        status="received",
        vendor="Stark Industries",
        amount=Decimal("9900"),
        po_number="PO-22760",
        confidence="HIGH",
    ),
    # ---- routine auto-clear ----
    Invoice(
        id="INV-4472",
        invoice_number="INV-4472",
        status="received",
        vendor="Globex Trading",
        amount=Decimal("2480"),
        po_number="PO-22845",
        confidence="HIGH",
    ),
    Invoice(
        id="INV-4475",
        invoice_number="INV-4475",
        status="received",
        vendor="Initech Software",
        amount=Decimal("1990"),
        po_number="PO-22848",
        confidence="HIGH",
    ),
    Invoice(
        id="INV-4478",
        invoice_number="INV-4478",
        status="received",
        vendor="Hooli Cloud",
        amount=Decimal("3450"),
        po_number="PO-22851",
        confidence="HIGH",
    ),
    Invoice(
        id="INV-4481",
        invoice_number="INV-4481",
        status="received",
        vendor="Soylent Foods",
        amount=Decimal("870"),
        po_number="PO-22853",
        confidence="HIGH",
    ),
    Invoice(
        id="INV-4485",
        invoice_number="INV-4485",
        status="received",
        vendor="Meridian Freight",
        amount=Decimal("4120"),
        po_number="PO-22855",
        confidence="HIGH",
    ),
    Invoice(
        id="INV-4489",
        invoice_number="INV-4489",
        status="received",
        vendor="Wayne Office Supply",
        amount=Decimal("640"),
        po_number="PO-22858",
        confidence="HIGH",
    ),
    Invoice(
        id="INV-4492",
        invoice_number="INV-4492",
        status="received",
        vendor="Umbrella Supplies",
        amount=Decimal("2870"),
        po_number="PO-22861",
        confidence="HIGH",
    ),
    Invoice(
        id="INV-4496",
        invoice_number="INV-4496",
        status="received",
        vendor="Globex Trading",
        amount=Decimal("5310"),
        po_number="PO-22863",
        confidence="HIGH",
    ),
    Invoice(
        id="INV-4499",
        invoice_number="INV-4499",
        status="received",
        vendor="Hooli Cloud",
        amount=Decimal("1280"),
        po_number="PO-22866",
        confidence="HIGH",
    ),
    Invoice(
        id="INV-4501",
        invoice_number="INV-4501",
        status="received",
        vendor="Initech Software",
        amount=Decimal("3990"),
        po_number="PO-22868",
        confidence="HIGH",
    ),
]

# ---------------------------------------------------------------------------
# Prior cleared invoice for the Stark DUPLICATE_EXACT hard-stop.
# Same vendor + same invoice_number as INV-4502.
# ---------------------------------------------------------------------------
_STARK_PRIOR = Invoice(
    id="INV-4461",
    invoice_number="INV-4502",     # Same invoice_number → DUPLICATE_EXACT
    status="cleared",
    vendor="Stark Industries",
    amount=Decimal("9900"),
    po_number="PO-22760",
    confidence="HIGH",
)

# ---------------------------------------------------------------------------
# Helpers to build the cold-start history rows.
# For each *approved* vendor that has routine invoices, we seed at least
# cold_start_n prior cleared invoices so the pipeline passes the cold-start
# check and AUTO_CLEARs them.
# ---------------------------------------------------------------------------
_ROUTINE_VENDORS = [
    "Globex Trading",
    "Initech Software",
    "Hooli Cloud",
    "Soylent Foods",
    "Meridian Freight",
    "Wayne Office Supply",
    "Umbrella Supplies",
]


def _make_cold_start_invoices(cold_start_n: int) -> list[Invoice]:
    rows: list[Invoice] = []
    for vendor in _ROUTINE_VENDORS:
        for i in range(cold_start_n):
            v_key = vendor.lower().replace(" ", "-")
            rows.append(
                Invoice(
                    id=f"hist-{v_key}-{i}",
                    invoice_number=f"HIST-{v_key.upper()}-{i}",
                    status="cleared",
                    vendor=vendor,
                    amount=Decimal("1000.00"),
                    confidence="HIGH",
                )
            )
    return rows


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def is_empty(s: Session) -> bool:
    """True if there are no Invoice rows with status == 'received'."""
    return (
        s.query(Invoice).filter(Invoice.status == "received").count() == 0
    )


def seed(s: Session, *, force: bool = False) -> int:
    """Insert the demo dataset.

    Parameters
    ----------
    s:
        An open SQLAlchemy Session.  The caller is responsible for commit.
    force:
        If True, wipe all Vendor / PurchaseOrder / Invoice / Rule /
        Correction / AuditEvent rows first, then re-insert.
        If False (default), this is a no-op when a received batch already
        exists (idempotent).

    Returns
    -------
    int
        Number of ``received`` batch invoices inserted (0 when idempotent
        no-op).
    """
    if force:
        s.query(AuditEvent).delete()
        s.query(Correction).delete()
        s.query(Rule).delete()
        s.query(Invoice).delete()
        s.query(PurchaseOrder).delete()
        s.query(Vendor).delete()
        s.flush()
    elif not is_empty(s):
        return 0

    settings = get_settings()

    # 1. Vendors
    for vendor in SEED_VENDORS:
        s.merge(vendor)

    # 2. POs
    for po in SEED_POS:
        s.merge(po)

    # 3. Cold-start history (cleared) for routine vendors
    for inv in _make_cold_start_invoices(settings.cold_start_n):
        s.merge(inv)

    # 4. Stark prior cleared (exact-duplicate prerequisite)
    s.merge(_STARK_PRIOR)

    s.flush()

    # 5. The received batch
    for inv in SEED_INVOICES:
        s.merge(inv)

    s.flush()

    return len(SEED_INVOICES)
