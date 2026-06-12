from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models.purchase_order import PurchaseOrder
import app.domain.policy.matching as matching_domain


def add(s: Session, po: PurchaseOrder) -> PurchaseOrder:
    s.add(po)
    s.flush()
    return po


def get_by_number(
    s: Session, po_number: str, *, org_id: str | None = None
) -> list[PurchaseOrder]:
    q = s.query(PurchaseOrder).filter(PurchaseOrder.po_number == po_number)
    if org_id is not None:
        q = q.filter(PurchaseOrder.org_id == org_id)
    return list(q.all())


def to_domain(po: PurchaseOrder) -> matching_domain.PurchaseOrder:
    return matching_domain.PurchaseOrder(
        po_number=po.po_number,
        vendor=po.vendor,
        amount=po.amount,
        remaining_balance=po.remaining_balance,
        po_id=po.id,
    )
