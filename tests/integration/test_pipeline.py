"""Integration tests for the process_invoice pipeline.

Four scenarios:
1. Auto-clear  — approved vendor, clean invoice within tolerance, HIGH confidence.
2. Escalate    — invoice 13% over PO → OVER_TOLERANCE warn → ESCALATE.
3. Block       — exact duplicate invoice number already cleared → BLOCK.
4. Injection-safe — unknown vendor, no PO → findings include UNKNOWN_VENDOR /
                     MISSING_PO warns → guard ESCALATES, never AUTO_CLEARs.
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.db.models.invoice import Invoice
from app.db.models.purchase_order import PurchaseOrder
from app.db.models.vendor import Vendor
from app.domain.decision.thresholds import Verdict
from app.domain.policy.matching import InvoiceData
from app.repositories import invoice_repo, po_repo, vendor_repo
from app.services import audit_service
from app.services.pipeline_service import process_invoice


# ---------------------------------------------------------------------------
# Seeding helpers
# ---------------------------------------------------------------------------


def _seed_vendor(s: Session, name: str, vid: str, status: str = "approved") -> Vendor:
    v = Vendor(id=vid, canonical_name=name, status=status)
    return vendor_repo.add(s, v)


def _seed_po(
    s: Session,
    *,
    pid: str,
    po_number: str,
    vendor: str,
    amount: str,
) -> PurchaseOrder:
    po = PurchaseOrder(
        id=pid,
        po_number=po_number,
        vendor=vendor,
        amount=Decimal(amount),
    )
    return po_repo.add(s, po)


def _seed_cleared_invoices(s: Session, vendor: str, count: int) -> None:
    """Seed enough cleared invoices to pass the cold-start check (cold_start_n=2)."""
    for i in range(count):
        invoice_repo.add(
            s,
            Invoice(
                id=f"hist-{vendor[:3]}-{i}",
                status="cleared",
                vendor=vendor,
                amount=Decimal("1000.00"),
                invoice_number=f"HIST-{vendor[:3]}-{i}",
            ),
        )


def _inv(
    invoice_id: str,
    vendor: str,
    amount: str,
    po_number: str | None,
    invoice_number: str,
) -> InvoiceData:
    return InvoiceData(
        invoice_id=invoice_id,
        vendor=vendor,
        amount=Decimal(amount),
        po_number=po_number,
        invoice_number=invoice_number,
    )


# ---------------------------------------------------------------------------
# 1. Auto-clear
# ---------------------------------------------------------------------------


def test_pipeline_auto_clear(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    """Approved vendor, matched PO, amount within tolerance, HIGH confidence,
    past cold-start → AUTO_CLEAR; invoice status becomes 'queued';
    audit chain intact; trail contains all expected stages + execution event."""

    vendor = "GlobalSupply"
    _seed_vendor(db, vendor, "v-gs")
    _seed_po(db, pid="po-gs-1", po_number="PO-GS-1", vendor=vendor, amount="5000.00")
    _seed_cleared_invoices(db, vendor, 2)  # cold_start_n=2

    inv = _inv("inv-ac-1", vendor, "5200.00", "PO-GS-1", "GSI-001")
    # 5200 / 5000 = 4% over — within tolerance_pct=0.05

    result = process_invoice(db, inv, confidence="HIGH")

    assert result.decision.verdict is Verdict.AUTO_CLEAR

    row = invoice_repo.get(db, "inv-ac-1")
    assert row is not None
    assert row.status == "queued"

    # Hash chain intact
    assert audit_service.verify(db) is True

    # Trail must contain extraction, enrichment, policy, guard, execution
    trail = audit_service.trail(db, "inv-ac-1")
    actions = [e.action for e in trail]
    assert "extracted_fields" in actions
    assert "resolved_vendor_matched_po" in actions
    assert "findings_computed" in actions
    assert any(a.startswith("verdict:") for a in actions)
    assert "executed:queued_payment" in actions


# ---------------------------------------------------------------------------
# 2. Escalate — over tolerance
# ---------------------------------------------------------------------------


def test_pipeline_escalate_over_tolerance(db: Session) -> None:
    """Invoice 13% over PO amount → OVER_TOLERANCE finding → ESCALATE;
    invoice status set to 'needs'; execution stage NOT reached."""

    vendor = "MegaParts"
    _seed_vendor(db, vendor, "v-mp")
    _seed_po(db, pid="po-mp-1", po_number="PO-MP-1", vendor=vendor, amount="10000.00")
    _seed_cleared_invoices(db, vendor, 2)

    inv = _inv("inv-esc-1", vendor, "11300.00", "PO-MP-1", "MPI-001")
    # 11300 / 10000 = 13% over tolerance (>5%)

    result = process_invoice(db, inv, confidence="HIGH")

    assert result.decision.verdict is Verdict.ESCALATE
    assert any(f.code == "OVER_TOLERANCE" for f in result.findings)

    row = invoice_repo.get(db, "inv-esc-1")
    assert row is not None
    assert row.status == "needs"

    # Execution must NOT have been called
    trail = audit_service.trail(db, "inv-esc-1")
    actions = [e.action for e in trail]
    assert "executed:queued_payment" not in actions


# ---------------------------------------------------------------------------
# 3. Block — exact duplicate
# ---------------------------------------------------------------------------


def test_pipeline_block_exact_duplicate(db: Session) -> None:
    """A second invoice with the same vendor + invoice_number as an already-cleared
    invoice → DUPLICATE_EXACT hard-stop → BLOCK; status 'blocked'; not executed."""

    vendor = "DuplicoCo"
    _seed_vendor(db, vendor, "v-dc")
    _seed_po(db, pid="po-dc-1", po_number="PO-DC-1", vendor=vendor, amount="3000.00")

    # Seed the already-cleared invoice (same vendor, same invoice_number "A-1")
    invoice_repo.add(
        db,
        Invoice(
            id="cleared-dc-1",
            status="cleared",
            vendor=vendor,
            amount=Decimal("3000.00"),
            invoice_number="A-1",
        ),
    )
    # Also seed extra cleared invoices so cold_start is met
    _seed_cleared_invoices(db, vendor, 2)

    inv = _inv("inv-dup-1", vendor, "3000.00", "PO-DC-1", "A-1")

    result = process_invoice(db, inv, confidence="HIGH")

    assert result.decision.verdict is Verdict.BLOCK
    assert any(f.code == "DUPLICATE_EXACT" for f in result.findings)

    row = invoice_repo.get(db, "inv-dup-1")
    assert row is not None
    assert row.status == "blocked"

    trail = audit_service.trail(db, "inv-dup-1")
    actions = [e.action for e in trail]
    assert "executed:queued_payment" not in actions


# ---------------------------------------------------------------------------
# 4. Injection-safe — unknown vendor, no PO
# ---------------------------------------------------------------------------


def test_pipeline_injection_safe_escalates(db: Session) -> None:
    """Invoice from an unknown/unapproved vendor with no PO reference.
    Policy yields UNKNOWN_VENDOR and MISSING_PO warnings (no HARD_STOP).
    Guard cannot AUTO_CLEAR (vendor not approved) → must ESCALATE.
    Execution must NOT be reached."""

    # Do NOT seed the vendor — it will be treated as 'new'/'unapproved'.
    inv = _inv("inv-inj-1", "UnknownPayNow Inc", "4000.00", None, "UPN-2024-001")

    result = process_invoice(db, inv, confidence="HIGH")

    # Injection attempt must ESCALATE, never AUTO_CLEAR
    assert result.decision.verdict is not Verdict.AUTO_CLEAR
    assert result.decision.verdict is Verdict.ESCALATE

    # Findings should include UNKNOWN_VENDOR and MISSING_PO
    finding_codes = {f.code for f in result.findings}
    assert "UNKNOWN_VENDOR" in finding_codes
    assert "MISSING_PO" in finding_codes

    row = invoice_repo.get(db, "inv-inj-1")
    assert row is not None
    assert row.status == "needs"

    trail = audit_service.trail(db, "inv-inj-1")
    actions = [e.action for e in trail]
    assert "executed:queued_payment" not in actions
