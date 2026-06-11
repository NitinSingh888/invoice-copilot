from decimal import Decimal
from app.domain.policy.findings import Severity
from app.domain.policy.matching import InvoiceData
from app.domain.policy.checks import check_duplicate

def _inv(inv_no, amount="100"):
    return InvoiceData("INV-NEW", "Acme", Decimal(amount), "PO-1", inv_no)

def test_exact_duplicate_is_hard_stop():
    cleared = [InvoiceData("INV-OLD", "Acme", Decimal("100"), "PO-1", "A-1")]
    f = check_duplicate(_inv("A-1"), cleared_exact=cleared, recent_same_amount=[])
    assert f.code == "DUPLICATE_EXACT" and f.severity is Severity.HARD_STOP
    assert "INV-OLD" in f.detail

def test_suspected_duplicate_is_warn():
    recent = [InvoiceData("INV-OLD", "Acme", Decimal("100"), "PO-1", "A-2")]
    f = check_duplicate(_inv("A-1"), cleared_exact=[], recent_same_amount=recent)
    assert f.code == "DUPLICATE_SUSPECT" and f.severity is Severity.WARN

def test_no_duplicate_returns_none():
    assert check_duplicate(_inv("A-1"), cleared_exact=[], recent_same_amount=[]) is None
