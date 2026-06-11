from __future__ import annotations

from decimal import Decimal

from app.domain.policy.findings import Severity
from app.domain.policy.matching import InvoiceData, POMatch, PurchaseOrder
from app.services.enrichment_service import Enrichment
from app.services.policy_service import run

_TOLERANCE = Decimal("0.05")


def _make_inv(
    vendor: str = "Acme Corp",
    amount: str = "1000.00",
    po_number: str | None = "PO-1",
    invoice_number: str = "INV-001",
) -> InvoiceData:
    return InvoiceData(
        invoice_id="inv-1",
        vendor=vendor,
        amount=Decimal(amount),
        po_number=po_number,
        invoice_number=invoice_number,
    )


def _make_po(amount: str = "1000.00", po_number: str = "PO-1") -> PurchaseOrder:
    return PurchaseOrder(po_number=po_number, vendor="Acme Corp", amount=Decimal(amount))


def test_clean_matched_invoice_gives_po_match_ok() -> None:
    po = _make_po()
    enr = Enrichment(
        vendor_status="approved",
        po_match=POMatch(po=po),
        cleared_exact=[],
        recent_same_amount=[],
    )
    findings = run(_make_inv(), enr, _TOLERANCE)
    codes = [f.code for f in findings]
    assert codes == ["PO_MATCH_OK"]
    assert all(f.severity == Severity.INFO for f in findings)


def test_invoice_13pct_over_po_contains_over_tolerance() -> None:
    po = _make_po(amount="1000.00")
    inv = _make_inv(amount="1130.00")  # 13% over
    enr = Enrichment(
        vendor_status="approved",
        po_match=POMatch(po=po),
        cleared_exact=[],
        recent_same_amount=[],
    )
    findings = run(inv, enr, _TOLERANCE)
    codes = [f.code for f in findings]
    assert "OVER_TOLERANCE" in codes


def test_exact_duplicate_contains_duplicate_exact() -> None:
    po = _make_po()
    inv = _make_inv()
    dup = InvoiceData(
        invoice_id="old-inv",
        vendor="Acme Corp",
        amount=Decimal("1000.00"),
        po_number="PO-1",
        invoice_number="INV-001",
    )
    enr = Enrichment(
        vendor_status="approved",
        po_match=POMatch(po=po),
        cleared_exact=[dup],
        recent_same_amount=[],
    )
    findings = run(inv, enr, _TOLERANCE)
    codes = [f.code for f in findings]
    assert "DUPLICATE_EXACT" in codes
    dup_finding = next(f for f in findings if f.code == "DUPLICATE_EXACT")
    assert dup_finding.severity == Severity.HARD_STOP


def test_unknown_vendor_contains_unknown_vendor() -> None:
    enr = Enrichment(
        vendor_status="new",
        po_match=POMatch(po=None),
        cleared_exact=[],
        recent_same_amount=[],
    )
    findings = run(_make_inv(po_number=None), enr, _TOLERANCE)
    codes = [f.code for f in findings]
    assert "UNKNOWN_VENDOR" in codes


def test_missing_po_no_po_match() -> None:
    enr = Enrichment(
        vendor_status="approved",
        po_match=POMatch(po=None),
        cleared_exact=[],
        recent_same_amount=[],
    )
    findings = run(_make_inv(po_number=None), enr, _TOLERANCE)
    codes = [f.code for f in findings]
    assert "MISSING_PO" in codes


def test_no_duplicate_findings_when_no_candidates() -> None:
    po = _make_po()
    enr = Enrichment(
        vendor_status="approved",
        po_match=POMatch(po=po),
        cleared_exact=[],
        recent_same_amount=[],
    )
    findings = run(_make_inv(), enr, _TOLERANCE)
    codes = [f.code for f in findings]
    assert "DUPLICATE_EXACT" not in codes
    assert "DUPLICATE_SUSPECT" not in codes
