from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.domain.policy.matching import InvoiceData, POMatch
from app.repositories import invoice_repo, po_repo, vendor_repo
from app.domain.policy.matching import match_po


@dataclass(frozen=True)
class Enrichment:
    vendor_status: str
    po_match: POMatch
    cleared_exact: list[InvoiceData]
    recent_same_amount: list[InvoiceData]


def enrich(s: Session, invoice_data: InvoiceData) -> Enrichment:
    settings = get_settings()

    vendor_status = vendor_repo.status_of(s, invoice_data.vendor)

    if invoice_data.po_number:
        pos = [po_repo.to_domain(p) for p in po_repo.get_by_number(s, invoice_data.po_number)]
    else:
        pos = []
    po_match = match_po(invoice_data, pos)

    cleared_exact_rows = invoice_repo.cleared_exact(s, invoice_data.vendor, invoice_data.invoice_number)
    cleared_exact = [invoice_repo.to_domain(i) for i in cleared_exact_rows]

    since = datetime.now(timezone.utc) - timedelta(days=settings.duplicate_window_days)
    recent_rows = invoice_repo.recent_same_amount(s, invoice_data.vendor, invoice_data.amount, since)
    recent_same_amount = [invoice_repo.to_domain(i) for i in recent_rows]

    return Enrichment(
        vendor_status=vendor_status,
        po_match=po_match,
        cleared_exact=cleared_exact,
        recent_same_amount=recent_same_amount,
    )
