from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.db.models.rule import Rule
from app.repositories import rule_repo


def _rule(id: str, vendor: str | None = None, status: str = "active",
          route: str = "auto_approve", max_over_pct: str | None = None,
          min_amount: str | None = None) -> Rule:
    return Rule(
        id=id,
        vendor=vendor,
        status=status,
        route=route,
        max_over_pct=Decimal(max_over_pct) if max_over_pct is not None else None,
        min_amount=Decimal(min_amount) if min_amount is not None else None,
    )


def test_add_and_get(db: Session) -> None:
    rule_repo.add(db, _rule("r1"))
    result = rule_repo.get(db, "r1")
    assert result is not None
    assert result.id == "r1"


def test_get_missing(db: Session) -> None:
    assert rule_repo.get(db, "ghost") is None


def test_list_all(db: Session) -> None:
    rule_repo.add(db, _rule("r1", status="active"))
    rule_repo.add(db, _rule("r2", status="disabled"))
    assert len(rule_repo.list_all(db)) == 2


def test_list_active(db: Session) -> None:
    rule_repo.add(db, _rule("r1", status="active"))
    rule_repo.add(db, _rule("r2", status="disabled"))
    rule_repo.add(db, _rule("r3", status="active"))
    active = rule_repo.list_active(db)
    assert len(active) == 2
    assert all(r.status == "active" for r in active)


def test_set_status(db: Session) -> None:
    rule_repo.add(db, _rule("r1", status="active"))
    updated = rule_repo.set_status(db, "r1", "disabled")
    assert updated.status == "disabled"
    # Persist persisted
    fetched = rule_repo.get(db, "r1")
    assert fetched is not None
    assert fetched.status == "disabled"


def test_set_status_missing(db: Session) -> None:
    with pytest.raises(ValueError, match="not found"):
        rule_repo.set_status(db, "ghost", "disabled")


def test_to_domain_maps_fields(db: Session) -> None:
    rule = rule_repo.add(
        db,
        _rule("r1", vendor="Acme Corp", status="active", route="escalate",
              max_over_pct="0.0500", min_amount="1000.00"),
    )
    domain = rule_repo.to_domain(rule)
    assert domain.id == "r1"
    assert domain.vendor == "Acme Corp"
    assert domain.max_over_pct == Decimal("0.0500")
    assert domain.route == "escalate"
    assert domain.status == "active"
    assert domain.min_amount == Decimal("1000.00")


def test_to_domain_none_fields(db: Session) -> None:
    rule = rule_repo.add(db, _rule("r2", vendor=None, max_over_pct=None, min_amount=None))
    domain = rule_repo.to_domain(rule)
    assert domain.vendor is None
    assert domain.max_over_pct is None
    assert domain.min_amount is None
