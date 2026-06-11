from __future__ import annotations
from decimal import Decimal
from collections.abc import Sequence
from .findings import Finding, Severity
from .matching import InvoiceData, PurchaseOrder, POMatch

def check_po_match(invoice: InvoiceData, match: POMatch) -> Finding:
    if match.ambiguous:
        return Finding("MULTI_PO_MATCH", Severity.WARN, "Multiple POs match this number")
    if match.po is None:
        if invoice.po_number:
            return Finding("NO_PO_MATCH", Severity.WARN, f"No PO {invoice.po_number}")
        return Finding("MISSING_PO", Severity.WARN, "No PO referenced")
    return Finding("PO_MATCH_OK", Severity.INFO, f"Matched {match.po.po_number}")

def check_tolerance(invoice: InvoiceData, po: PurchaseOrder, tolerance_pct: Decimal) -> Finding | None:
    diff = invoice.amount - po.amount
    if po.amount == 0 or diff == 0:
        return None
    pct = diff / po.amount
    if pct > tolerance_pct:
        return Finding("OVER_TOLERANCE", Severity.WARN, f"{pct:.0%} over PO")
    if pct < -tolerance_pct:
        return Finding("UNDER_TOLERANCE", Severity.WARN, f"{abs(pct):.0%} under PO")
    return None

def check_partial_po(invoice: InvoiceData, po: PurchaseOrder) -> Finding | None:
    if po.remaining_balance is None:
        return None
    if po.remaining_balance < po.amount and invoice.amount <= po.remaining_balance:
        return Finding("PARTIAL_PO", Severity.WARN, "PO is only partly fulfilled")
    return None

def check_vendor(vendor_status: str) -> Finding | None:
    if vendor_status == "approved":
        return None
    if vendor_status == "blocked":
        return Finding("VENDOR_BLOCKED", Severity.HARD_STOP, "Vendor is blocked")
    return Finding("UNKNOWN_VENDOR", Severity.WARN, "Vendor not yet approved")

def check_duplicate(
    invoice: InvoiceData,
    cleared_exact: Sequence[InvoiceData],
    recent_same_amount: Sequence[InvoiceData],
) -> Finding | None:
    """Exact = same (vendor, invoice_number) already cleared → hard stop.
    Suspect = same (vendor, amount) recently, different/missing invoice number → warn.
    Caller is responsible for pre-filtering the two candidate lists by vendor/window."""
    for c in cleared_exact:
        if c.vendor == invoice.vendor and c.invoice_number == invoice.invoice_number:
            return Finding("DUPLICATE_EXACT", Severity.HARD_STOP, f"Already cleared as {c.invoice_id}")
    for c in recent_same_amount:
        if (c.vendor == invoice.vendor and c.amount == invoice.amount
                and c.invoice_number != invoice.invoice_number):
            return Finding("DUPLICATE_SUSPECT", Severity.WARN, "Same vendor + amount seen recently")
    return None
