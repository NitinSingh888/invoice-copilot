from __future__ import annotations

from datetime import datetime, timezone, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.db.models.invoice import Invoice
from app.repositories import invoice_repo


def _inv(
    id: str,
    status: str = "received",
    vendor: str | None = "Acme Corp",
    amount: str | None = "1000.00",
    invoice_number: str | None = "INV-001",
    po_number: str | None = None,
    created_at: datetime | None = None,
) -> Invoice:
    kwargs: dict[str, object] = dict(
        id=id,
        status=status,
        vendor=vendor,
        amount=Decimal(amount) if amount is not None else None,
        invoice_number=invoice_number,
        po_number=po_number,
    )
    if created_at is not None:
        kwargs["created_at"] = created_at
    return Invoice(**kwargs)


NOW = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
BEFORE = NOW - timedelta(days=10)
AFTER = NOW - timedelta(days=1)


def test_add_and_get(db: Session) -> None:
    invoice_repo.add(db, _inv("i1"))
    result = invoice_repo.get(db, "i1")
    assert result is not None
    assert result.id == "i1"


def test_get_missing(db: Session) -> None:
    assert invoice_repo.get(db, "ghost") is None


def test_list_all(db: Session) -> None:
    invoice_repo.add(db, _inv("i1"))
    invoice_repo.add(db, _inv("i2", status="cleared"))
    assert len(invoice_repo.list_all(db)) == 2


def test_list_by_status(db: Session) -> None:
    invoice_repo.add(db, _inv("i1", status="received"))
    invoice_repo.add(db, _inv("i2", status="cleared"))
    invoice_repo.add(db, _inv("i3", status="cleared"))
    cleared = invoice_repo.list_by_status(db, "cleared")
    assert len(cleared) == 2
    assert all(i.status == "cleared" for i in cleared)
    received = invoice_repo.list_by_status(db, "received")
    assert len(received) == 1


def test_set_status(db: Session) -> None:
    invoice_repo.add(db, _inv("i1", status="received"))
    updated = invoice_repo.set_status(db, "i1", "cleared", verdict="AUTO_CLEAR", route="auto")
    assert updated.status == "cleared"
    assert updated.verdict == "AUTO_CLEAR"
    assert updated.route == "auto"


def test_set_status_missing(db: Session) -> None:
    with pytest.raises(ValueError, match="not found"):
        invoice_repo.set_status(db, "ghost", "cleared")


def test_cleared_exact(db: Session) -> None:
    invoice_repo.add(db, _inv("i1", status="cleared", vendor="Acme Corp", invoice_number="INV-42"))
    invoice_repo.add(db, _inv("i2", status="queued", vendor="Acme Corp", invoice_number="INV-42"))
    invoice_repo.add(db, _inv("i3", status="received", vendor="Acme Corp", invoice_number="INV-42"))
    invoice_repo.add(db, _inv("i4", status="cleared", vendor="Beta LLC", invoice_number="INV-42"))
    invoice_repo.add(db, _inv("i5", status="cleared", vendor="Acme Corp", invoice_number="INV-99"))

    results = invoice_repo.cleared_exact(db, "Acme Corp", "INV-42")
    ids = {r.id for r in results}
    assert ids == {"i1", "i2"}  # cleared + queued, same vendor + invoice_number


def test_recent_same_amount(db: Session) -> None:
    invoice_repo.add(db, _inv("i1", amount="500.00", created_at=BEFORE))
    invoice_repo.add(db, _inv("i2", amount="500.00", created_at=AFTER))
    invoice_repo.add(db, _inv("i3", amount="999.00", created_at=AFTER))

    # Cutoff: NOW - 5 days → only AFTER (NOW-1d) qualifies
    cutoff = NOW - timedelta(days=5)
    results = invoice_repo.recent_same_amount(db, "Acme Corp", Decimal("500.00"), cutoff)
    ids = {r.id for r in results}
    assert ids == {"i2"}


def test_count_cleared_for_vendor(db: Session) -> None:
    invoice_repo.add(db, _inv("i1", status="cleared", vendor="Acme Corp"))
    invoice_repo.add(db, _inv("i2", status="queued", vendor="Acme Corp"))
    invoice_repo.add(db, _inv("i3", status="received", vendor="Acme Corp"))
    invoice_repo.add(db, _inv("i4", status="cleared", vendor="Other Co"))

    assert invoice_repo.count_cleared_for_vendor(db, "Acme Corp") == 2
    assert invoice_repo.count_cleared_for_vendor(db, "Other Co") == 1
    assert invoice_repo.count_cleared_for_vendor(db, "Nobody") == 0


def test_to_domain(db: Session) -> None:
    inv = invoice_repo.add(
        db,
        _inv("i1", vendor="Acme Corp", amount="1500.00", invoice_number="INV-7", po_number="PO-99"),
    )
    domain = invoice_repo.to_domain(inv)
    assert domain.invoice_id == "i1"
    assert domain.vendor == "Acme Corp"
    assert domain.amount == Decimal("1500.00")
    assert domain.po_number == "PO-99"
    assert domain.invoice_number == "INV-7"
