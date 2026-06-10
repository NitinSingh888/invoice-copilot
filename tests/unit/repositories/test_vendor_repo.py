from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.db.models.vendor import Vendor
from app.repositories import vendor_repo


@pytest.fixture
def acme(db: Session) -> Vendor:
    v = Vendor(
        id="v1",
        canonical_name="Acme Corp",
        aliases=["ACME", "Acme Corporation"],
        status="approved",
    )
    return vendor_repo.add(db, v)


def test_add_and_get(db: Session, acme: Vendor) -> None:
    result = vendor_repo.get(db, "v1")
    assert result is not None
    assert result.id == "v1"
    assert result.canonical_name == "Acme Corp"


def test_get_missing(db: Session) -> None:
    assert vendor_repo.get(db, "nonexistent") is None


def test_resolve_exact(db: Session, acme: Vendor) -> None:
    assert vendor_repo.resolve(db, "Acme Corp") is acme


def test_resolve_normalised_canonical(db: Session, acme: Vendor) -> None:
    # Multiple spaces + different case
    assert vendor_repo.resolve(db, "  acme   corp ") is acme


def test_resolve_alias_exact(db: Session, acme: Vendor) -> None:
    assert vendor_repo.resolve(db, "ACME") is acme


def test_resolve_alias_normalised(db: Session, acme: Vendor) -> None:
    # "Acme Corporation" is an alias; resolve by its normalised form
    assert vendor_repo.resolve(db, "acme corporation") is acme


def test_resolve_unknown(db: Session, acme: Vendor) -> None:
    assert vendor_repo.resolve(db, "Unknown Inc") is None


def test_status_of_known(db: Session, acme: Vendor) -> None:
    assert vendor_repo.status_of(db, "Acme Corp") == "approved"


def test_status_of_unknown(db: Session, acme: Vendor) -> None:
    assert vendor_repo.status_of(db, "Unknown Inc") == "new"
