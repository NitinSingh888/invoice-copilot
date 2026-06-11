"""Demo seed dataset — built from REAL invoice PDFs.

Extracted fields are cached in ``data/extracted_samples.json``; no LLM is
called at seed time.

Intended pipeline outcomes for the 10 received invoices:

AUTO_CLEAR (4):
    inv-azure      Azure Interior        $279.84  HIGH   PO match, approved vendor
    inv-flipkart   WS Retail             $319.00  HIGH   PO match, approved vendor
    inv-netpresse  NETPRESSE             $56.02   HIGH   PO match, approved vendor
    inv-quality    QualityHosting AG     $34.73   HIGH   PO match, approved vendor

ESCALATE over-PO (2):
    inv-coolblue-1 Coolblue B.V.         $717.97  HIGH   PO 7% under → OVER_TOLERANCE
    inv-coolblue-2 Coolblue B.V.         $4904.94 MED    PO 7% under + MED conf

ESCALATE low-confidence / unknown vendor (3):
    inv-aws        Amazon Web Services   $4.11    LOW    no PO, LOW conf
    inv-free       Free SAS              $29.99   LOW    no PO, LOW conf
    inv-oyo        OYO / Oravel Stays    $1939    LOW    unknown vendor, no PO

BLOCK duplicate (1):
    inv-saeco      SAECO                 $49.99   MED    exact duplicate (prior cleared)
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
# SEED_VENDORS
# ---------------------------------------------------------------------------

SEED_VENDORS: list[Vendor] = [
    # AUTO_CLEAR vendors — approved
    Vendor(
        id="v-azure",
        canonical_name="Azure Interior",
        aliases=[],
        status="approved",
        default_approver="Priya",
    ),
    Vendor(
        id="v-flipkart",
        canonical_name="WS Retail Services Pvt. Ltd",
        aliases=["WS Retail"],
        status="approved",
        default_approver="Priya",
    ),
    Vendor(
        id="v-netpresse",
        canonical_name="NETPRESSE",
        aliases=[],
        status="approved",
        default_approver="Priya",
    ),
    Vendor(
        id="v-quality",
        canonical_name="QualityHosting AG",
        aliases=["QualityHosting"],
        status="approved",
        default_approver="Priya",
    ),
    # ESCALATE over-PO vendor — approved but invoices are over-tolerance
    Vendor(
        id="v-coolblue",
        canonical_name="Coolblue B.V.",
        aliases=["Coolblue"],
        status="approved",
        default_approver="Priya",
    ),
    # ESCALATE — approved vendor but LOW confidence / no PO
    Vendor(
        id="v-aws",
        canonical_name="Amazon Web Services, Inc.",
        aliases=["AWS", "Amazon Web Services"],
        status="approved",
        default_approver="Priya",
    ),
    Vendor(
        id="v-free",
        canonical_name="Free SAS",
        aliases=["Free"],
        status="approved",
        default_approver="Priya",
    ),
    # ESCALATE — unknown vendor (status=new)
    Vendor(
        id="v-oyo",
        canonical_name="OYO / Oravel Stays Private Limited",
        aliases=["OYO"],
        status="new",
        default_approver="Priya",
    ),
    # BLOCK duplicate — approved vendor, prior cleared invoice with same invoice_number
    Vendor(
        id="v-saeco",
        canonical_name="SAECO",
        aliases=[],
        status="approved",
        default_approver="Priya",
    ),
]

# ---------------------------------------------------------------------------
# SEED_POS
# Amounts for AUTO_CLEAR POs: exactly equal to invoice amount (within tolerance).
# Amounts for ESCALATE over-PO: set ~7% BELOW invoice amount (over tolerance).
# SAECO PO exists but duplicate check fires first.
# AWS, Free SAS, OYO: no PO referenced on their invoices.
# ---------------------------------------------------------------------------

SEED_POS: list[PurchaseOrder] = [
    # -- AUTO_CLEAR POs (PO amount == invoice amount) --
    PurchaseOrder(
        id="po-azure-custref123",
        po_number="CUSTREF123",
        vendor="Azure Interior",
        amount=Decimal("279.84"),
    ),
    PurchaseOrder(
        id="po-flipkart-od",
        po_number="OD304175096047380001",
        vendor="WS Retail Services Pvt. Ltd",
        amount=Decimal("319.00"),
    ),
    PurchaseOrder(
        id="po-netpresse-365146",
        po_number="365146",
        vendor="NETPRESSE",
        amount=Decimal("56.02"),
    ),
    PurchaseOrder(
        id="po-quality-con02858",
        po_number="CON02858",
        vendor="QualityHosting AG",
        amount=Decimal("34.73"),
    ),
    # -- ESCALATE over-PO: PO amounts ~7% under invoice amounts --
    # coolblue-1 invoice: $717.97 → PO: $670.99 (6.7% under)
    PurchaseOrder(
        id="po-coolblue-12572103",
        po_number="12572103",
        vendor="Coolblue B.V.",
        amount=Decimal("670.99"),
    ),
    # coolblue-2 invoice: $4904.94 → PO: $4584.06 (6.7% under)
    PurchaseOrder(
        id="po-coolblue-12508334",
        po_number="12508334",
        vendor="Coolblue B.V.",
        amount=Decimal("4584.06"),
    ),
    # -- SAECO PO (blocked by duplicate before PO check matters) --
    PurchaseOrder(
        id="po-saeco-sconl",
        po_number="SCONL000000444",
        vendor="SAECO",
        amount=Decimal("49.99"),
    ),
]

# ---------------------------------------------------------------------------
# The received batch of 10 real invoices
# ---------------------------------------------------------------------------

SEED_INVOICES: list[Invoice] = [
    # ---- AUTO_CLEAR (4) ----
    Invoice(
        id="inv-azure",
        invoice_number="INV/2023/03/0008",
        status="received",
        vendor="Azure Interior",
        amount=Decimal("279.84"),
        po_number="CUSTREF123",
        confidence="HIGH",
        source_file="AzureInterior.pdf",
    ),
    Invoice(
        id="inv-flipkart",
        invoice_number="BLR_WFLD20151000982590",
        status="received",
        vendor="WS Retail Services Pvt. Ltd",
        amount=Decimal("319.00"),
        po_number="OD304175096047380001",
        confidence="HIGH",
        source_file="FlipkartInvoice.pdf",
    ),
    Invoice(
        id="inv-netpresse",
        invoice_number="2022089083",
        status="received",
        vendor="NETPRESSE",
        amount=Decimal("56.02"),
        po_number="365146",
        confidence="HIGH",
        source_file="NetpresseInvoice.pdf",
    ),
    Invoice(
        id="inv-quality",
        invoice_number="47774",
        status="received",
        vendor="QualityHosting AG",
        amount=Decimal("34.73"),
        po_number="CON02858",
        confidence="HIGH",
        source_file="QualityHosting.pdf",
    ),
    # ---- ESCALATE over-PO (2) ----
    Invoice(
        id="inv-coolblue-1",
        invoice_number="993548900",
        status="received",
        vendor="Coolblue B.V.",
        amount=Decimal("717.97"),
        po_number="12572103",
        confidence="HIGH",
        source_file="coolblue1.pdf",
    ),
    Invoice(
        id="inv-coolblue-2",
        invoice_number="992288600",
        status="received",
        vendor="Coolblue B.V.",
        amount=Decimal("4904.94"),
        po_number="12508334",
        confidence="MED",
        source_file="coolblue2.pdf",
    ),
    # ---- ESCALATE low-confidence / unknown vendor (3) ----
    Invoice(
        id="inv-aws",
        invoice_number="42183017",
        status="received",
        vendor="Amazon Web Services, Inc.",
        amount=Decimal("4.11"),
        po_number=None,
        confidence="LOW",
        source_file="AmazonWebServices.pdf",
    ),
    Invoice(
        id="inv-free",
        invoice_number="562044387",
        status="received",
        vendor="Free SAS",
        amount=Decimal("29.99"),
        po_number=None,
        confidence="LOW",
        source_file="free_fiber.pdf",
    ),
    Invoice(
        id="inv-oyo",
        invoice_number="IBZY2087",
        status="received",
        vendor="OYO / Oravel Stays Private Limited",
        amount=Decimal("1939"),
        po_number=None,
        confidence="LOW",
        source_file="oyo.pdf",
    ),
    # ---- BLOCK duplicate (1) ----
    Invoice(
        id="inv-saeco",
        invoice_number="VF1005193039SCONL0303006280999",
        status="received",
        vendor="SAECO",
        amount=Decimal("49.99"),
        po_number="SCONL000000444",
        confidence="MED",
        source_file="saeco.pdf",
    ),
]

# ---------------------------------------------------------------------------
# Prior cleared invoice for the SAECO DUPLICATE_EXACT hard-stop.
# Same vendor + same invoice_number as inv-saeco.
# ---------------------------------------------------------------------------
_SAECO_PRIOR = Invoice(
    id="inv-saeco-prior",
    invoice_number="VF1005193039SCONL0303006280999",  # Same invoice_number → DUPLICATE_EXACT
    status="cleared",
    vendor="SAECO",
    amount=Decimal("49.99"),
    po_number="SCONL000000444",
    confidence="MED",
    source_file="saeco.pdf",
)

# ---------------------------------------------------------------------------
# Cold-start history vendors — each needs at least cold_start_n cleared invoices
# so the pipeline passes the cold-start check and AUTO_CLEARs them.
# ---------------------------------------------------------------------------
_AUTO_CLEAR_VENDORS = [
    "Azure Interior",
    "WS Retail Services Pvt. Ltd",
    "NETPRESSE",
    "QualityHosting AG",
]

# Coolblue needs cold-start too (it escalates for over-tolerance, not cold-start)
_ESCALATE_OVER_PO_VENDORS = [
    "Coolblue B.V.",
]


def _make_cold_start_invoices(cold_start_n: int) -> list[Invoice]:
    rows: list[Invoice] = []
    all_vendors = _AUTO_CLEAR_VENDORS + _ESCALATE_OVER_PO_VENDORS
    for vendor in all_vendors:
        for i in range(cold_start_n):
            v_key = vendor.lower().replace(" ", "-").replace(".", "").replace("/", "-")
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
    """Insert the demo dataset from real invoice PDFs.

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

    # 3. Cold-start history (cleared) for auto-clear + over-PO vendors
    for inv in _make_cold_start_invoices(settings.cold_start_n):
        s.merge(inv)

    # 4. SAECO prior cleared (exact-duplicate prerequisite)
    s.merge(_SAECO_PRIOR)

    s.flush()

    # 5. The received batch
    for inv in SEED_INVOICES:
        s.merge(inv)

    s.flush()

    return len(SEED_INVOICES)
