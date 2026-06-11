from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.db.models.purchase_order import PurchaseOrder
from app.repositories import po_repo


def _make_po(id: str, po_number: str, vendor: str, amount: str, remaining: str | None = None) -> PurchaseOrder:
    return PurchaseOrder(
        id=id,
        po_number=po_number,
        vendor=vendor,
        amount=Decimal(amount),
        remaining_balance=Decimal(remaining) if remaining is not None else None,
    )


def test_add_and_get_by_number(db: Session) -> None:
    po = _make_po("po1", "PO-100", "Acme Corp", "1000.00", "800.00")
    po_repo.add(db, po)
    result = po_repo.get_by_number(db, "PO-100")
    assert len(result) == 1
    assert result[0].id == "po1"


def test_get_by_number_returns_all_matches(db: Session) -> None:
    po1 = _make_po("po1", "PO-200", "Acme Corp", "1000.00")
    po2 = _make_po("po2", "PO-200", "Beta LLC", "2000.00")
    po_repo.add(db, po1)
    po_repo.add(db, po2)
    results = po_repo.get_by_number(db, "PO-200")
    assert len(results) == 2
    ids = {r.id for r in results}
    assert ids == {"po1", "po2"}


def test_get_by_number_missing(db: Session) -> None:
    assert po_repo.get_by_number(db, "PO-NONE") == []


def test_to_domain_maps_fields(db: Session) -> None:
    po = _make_po("po3", "PO-300", "Gamma Inc", "5000.00", "4500.50")
    po_repo.add(db, po)
    domain_po = po_repo.to_domain(po)
    assert domain_po.po_number == "PO-300"
    assert domain_po.vendor == "Gamma Inc"
    assert domain_po.amount == Decimal("5000.00")
    assert domain_po.remaining_balance == Decimal("4500.50")


def test_to_domain_remaining_balance_none(db: Session) -> None:
    po = _make_po("po4", "PO-400", "Delta Co", "9999.99")
    po_repo.add(db, po)
    domain_po = po_repo.to_domain(po)
    assert domain_po.remaining_balance is None
