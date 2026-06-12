from __future__ import annotations

from datetime import datetime, timezone, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.db.models.correction import Correction
from app.db.models.invoice import Invoice
from app.repositories import correction_repo


def _add_invoice(db: Session, inv_id: str) -> None:
    """Helper: insert a minimal invoice row to satisfy the FK."""
    db.add(Invoice(id=inv_id, vendor="Test", amount=Decimal("100")))
    db.flush()


def _corr(
    id: str,
    vendor: str = "Acme Corp",
    invoice_id: str = "INV-1",
    finding_code: str = "OVER_BILLED",
    user_action: str = "approve",
    over_pct: str = "0.0200",
    created_at: datetime | None = None,
) -> Correction:
    kwargs: dict[str, object] = dict(
        id=id,
        invoice_id=invoice_id,
        vendor=vendor,
        finding_code=finding_code,
        user_action=user_action,
        over_pct=Decimal(over_pct),
    )
    if created_at is not None:
        kwargs["created_at"] = created_at
    return Correction(**kwargs)


def test_add_and_list_for_vendor(db: Session) -> None:
    _add_invoice(db, "INV-1")
    correction_repo.add(db, _corr("c1", vendor="Acme Corp"))
    correction_repo.add(db, _corr("c2", vendor="Beta LLC"))
    correction_repo.add(db, _corr("c3", vendor="Acme Corp"))
    results = correction_repo.list_for_vendor(db, "Acme Corp")
    ids = {c.id for c in results}
    assert ids == {"c1", "c3"}


def test_list_for_vendor_empty(db: Session) -> None:
    assert correction_repo.list_for_vendor(db, "Nobody") == []


def test_list_recent_order(db: Session) -> None:
    _add_invoice(db, "INV-1")
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    for i in range(5):
        correction_repo.add(db, _corr(f"c{i}", created_at=base + timedelta(days=i)))
    recent = correction_repo.list_recent(db, limit=3)
    assert len(recent) == 3
    # Should be newest first
    assert recent[0].id == "c4"
    assert recent[1].id == "c3"
    assert recent[2].id == "c2"


def test_list_recent_default_limit(db: Session) -> None:
    _add_invoice(db, "INV-1")
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    for i in range(60):
        correction_repo.add(db, _corr(f"c{i:03d}", created_at=base + timedelta(hours=i)))
    recent = correction_repo.list_recent(db)
    assert len(recent) == 50


def test_to_domain_maps_fields(db: Session) -> None:
    _add_invoice(db, "INV-99")
    c = correction_repo.add(
        db,
        _corr("c1", vendor="Acme Corp", invoice_id="INV-99",
              finding_code="OVER_BILLED", user_action="approve", over_pct="0.0350"),
    )
    domain = correction_repo.to_domain(c)
    assert domain.invoice_id == "INV-99"
    assert domain.vendor == "Acme Corp"
    assert domain.finding_code == "OVER_BILLED"
    assert domain.user_action == "approve"
    assert domain.over_pct == Decimal("0.0350")
