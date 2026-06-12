from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.db.models.invoice import Invoice
import app.domain.policy.matching as matching_domain

_CLEARED_STATUSES = ("cleared", "queued")


def add(s: Session, inv: Invoice) -> Invoice:
    s.add(inv)
    s.flush()
    return inv


def get(s: Session, invoice_id: str, *, org_id: str | None = None) -> Invoice | None:
    inv = s.get(Invoice, invoice_id)
    if inv is None:
        return None
    if org_id is not None and inv.org_id != org_id:
        return None
    return inv


def get_by_invoice_number(
    s: Session, invoice_number: str, *, org_id: str | None = None
) -> Invoice | None:
    """Find an invoice by its (vendor-assigned) invoice_number — any format."""
    q = s.query(Invoice).filter(Invoice.invoice_number == invoice_number)
    if org_id is not None:
        q = q.filter(Invoice.org_id == org_id)
    return q.order_by(Invoice.created_at.desc()).first()


def list_all(s: Session, *, org_id: str | None = None) -> list[Invoice]:
    q = s.query(Invoice).filter(Invoice.is_deleted.is_(False))
    if org_id is not None:
        q = q.filter(Invoice.org_id == org_id)
    return list(q.all())


def list_by_status(s: Session, status: str, *, org_id: str | None = None) -> list[Invoice]:
    q = s.query(Invoice).filter(Invoice.status == status)
    if org_id is not None:
        q = q.filter(Invoice.org_id == org_id)
    return list(q.all())


def list_today(s: Session, *, org_id: str | None = None) -> list[Invoice]:
    """Invoices created today (UTC) — i.e. the live working queue, excluding
    the multi-day history. Used as the default scope for conversational queries."""
    from datetime import timezone

    start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    q = s.query(Invoice).filter(
        Invoice.is_deleted.is_(False), Invoice.created_at >= start
    )
    if org_id is not None:
        q = q.filter(Invoice.org_id == org_id)
    return list(q.all())


def set_status(s: Session, invoice_id: str, status: str, **fields: Any) -> Invoice:
    inv = s.get(Invoice, invoice_id)
    if inv is None:
        raise ValueError(f"Invoice {invoice_id!r} not found")
    inv.status = status
    for col, val in fields.items():
        setattr(inv, col, val)
    s.flush()
    return inv


def cleared_exact(
    s: Session, vendor: str, invoice_number: str, *, org_id: str | None = None
) -> list[Invoice]:
    q = s.query(Invoice).filter(
        Invoice.status.in_(_CLEARED_STATUSES),
        Invoice.vendor == vendor,
        Invoice.invoice_number == invoice_number,
    )
    if org_id is not None:
        q = q.filter(Invoice.org_id == org_id)
    return list(q.all())


def recent_same_amount(
    s: Session,
    vendor: str,
    amount: Decimal,
    since: datetime,
    *,
    org_id: str | None = None,
) -> list[Invoice]:
    q = s.query(Invoice).filter(
        Invoice.vendor == vendor,
        Invoice.amount == amount,
        Invoice.created_at >= since,
    )
    if org_id is not None:
        q = q.filter(Invoice.org_id == org_id)
    return list(q.all())


def count_cleared_for_vendor(s: Session, vendor: str, *, org_id: str | None = None) -> int:
    q = s.query(Invoice).filter(
        Invoice.status.in_(_CLEARED_STATUSES),
        Invoice.vendor == vendor,
    )
    if org_id is not None:
        q = q.filter(Invoice.org_id == org_id)
    return int(q.count())


def to_domain(inv: Invoice) -> matching_domain.InvoiceData:
    # amount may be None for some invoices, but domain expects Decimal;
    # callers that use to_domain must ensure amount is set.
    amount: Decimal = inv.amount if inv.amount is not None else Decimal("0")
    invoice_number: str = inv.invoice_number if inv.invoice_number is not None else ""
    vendor: str = inv.vendor if inv.vendor is not None else ""
    return matching_domain.InvoiceData(
        invoice_id=inv.id,
        vendor=vendor,
        amount=amount,
        po_number=inv.po_number,
        invoice_number=invoice_number,
    )
