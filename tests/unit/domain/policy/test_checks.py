from decimal import Decimal
from app.domain.policy.findings import Severity
from app.domain.policy.matching import InvoiceData, PurchaseOrder, POMatch
from app.domain.policy.checks import (
    check_po_match, check_tolerance, check_partial_po, check_vendor,
)

def _inv(amount, po_number="PO-1"):
    return InvoiceData("INV-1", "Acme", Decimal(amount), po_number, "A-1")

def test_check_po_match_ok():
    po = PurchaseOrder("PO-1", "Acme", Decimal("100"))
    f = check_po_match(_inv("100"), POMatch(po=po))
    assert f.code == "PO_MATCH_OK" and f.severity is Severity.INFO

def test_check_po_match_ambiguous():
    f = check_po_match(_inv("100"), POMatch(po=None, ambiguous=True))
    assert f.code == "MULTI_PO_MATCH" and f.severity is Severity.WARN

def test_check_po_missing_vs_unmatched():
    assert check_po_match(_inv("100", None), POMatch(None)).code == "MISSING_PO"
    assert check_po_match(_inv("100", "PO-X"), POMatch(None)).code == "NO_PO_MATCH"

def test_tolerance_within_returns_none():
    po = PurchaseOrder("PO-1", "Acme", Decimal("100"))
    assert check_tolerance(_inv("104"), po, Decimal("0.05")) is None  # 4% <= 5%

def test_tolerance_over():
    po = PurchaseOrder("PO-1", "Acme", Decimal("100"))
    f = check_tolerance(_inv("113"), po, Decimal("0.05"))
    assert f.code == "OVER_TOLERANCE" and f.severity is Severity.WARN

def test_tolerance_under():
    po = PurchaseOrder("PO-1", "Acme", Decimal("100"))
    f = check_tolerance(_inv("80"), po, Decimal("0.05"))
    assert f.code == "UNDER_TOLERANCE"

def test_partial_po_flags_when_po_partly_fulfilled():
    po = PurchaseOrder("PO-1", "Acme", Decimal("100"), remaining_balance=Decimal("40"))
    f = check_partial_po(_inv("30"), po)  # 30 <= remaining 40, but PO partly used
    assert f.code == "PARTIAL_PO" and f.severity is Severity.WARN

def test_vendor_status():
    assert check_vendor("approved") is None
    assert check_vendor("new").code == "UNKNOWN_VENDOR"
    assert check_vendor("blocked").severity is Severity.HARD_STOP
