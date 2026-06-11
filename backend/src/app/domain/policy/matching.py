from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from collections.abc import Sequence

@dataclass(frozen=True)
class PurchaseOrder:
    po_number: str
    vendor: str
    amount: Decimal
    remaining_balance: Decimal | None = None

@dataclass(frozen=True)
class InvoiceData:
    invoice_id: str
    vendor: str
    amount: Decimal
    po_number: str | None
    invoice_number: str

@dataclass(frozen=True)
class POMatch:
    po: PurchaseOrder | None
    ambiguous: bool = False

def match_po(invoice: InvoiceData, pos: Sequence[PurchaseOrder]) -> POMatch:
    if not invoice.po_number:
        return POMatch(po=None)
    candidates = [p for p in pos if p.po_number == invoice.po_number]
    if len(candidates) == 0:
        return POMatch(po=None)
    if len(candidates) > 1:
        return POMatch(po=None, ambiguous=True)
    return POMatch(po=candidates[0])
