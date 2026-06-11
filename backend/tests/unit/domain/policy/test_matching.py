from decimal import Decimal
from app.domain.policy.matching import InvoiceData, PurchaseOrder, match_po

def _inv(po_number):
    return InvoiceData(invoice_id="INV-1", vendor="Acme", amount=Decimal("100"),
                       po_number=po_number, invoice_number="A-1")

def test_match_single_po():
    pos = [PurchaseOrder("PO-1", "Acme", Decimal("100"))]
    m = match_po(_inv("PO-1"), pos)
    assert m.po is pos[0] and m.ambiguous is False

def test_no_po_number_returns_none():
    m = match_po(_inv(None), [PurchaseOrder("PO-1", "Acme", Decimal("100"))])
    assert m.po is None and m.ambiguous is False

def test_unmatched_po_number_returns_none():
    m = match_po(_inv("PO-9"), [PurchaseOrder("PO-1", "Acme", Decimal("100"))])
    assert m.po is None and m.ambiguous is False

def test_multiple_matches_is_ambiguous():
    pos = [PurchaseOrder("PO-1", "Acme", Decimal("100")),
           PurchaseOrder("PO-1", "Acme", Decimal("200"))]
    m = match_po(_inv("PO-1"), pos)
    assert m.po is None and m.ambiguous is True
