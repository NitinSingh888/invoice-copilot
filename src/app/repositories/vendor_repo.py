from __future__ import annotations

import re

from sqlalchemy.orm import Session

from app.db.models.vendor import Vendor


def _normalize(name: str) -> str:
    """Lower-case, strip, and collapse internal whitespace."""
    return re.sub(r"\s+", " ", name.strip().lower())


def add(s: Session, vendor: Vendor) -> Vendor:
    s.add(vendor)
    s.flush()
    return vendor


def get(s: Session, vendor_id: str) -> Vendor | None:
    return s.get(Vendor, vendor_id)


def resolve(s: Session, name: str) -> Vendor | None:
    """Alias-aware vendor lookup.

    Priority:
    1. Exact match on canonical_name.
    2. Case/whitespace-normalised match on canonical_name.
    3. Raw ``name`` or its normalised form appears in a vendor's ``aliases``.
    """
    # 1. Exact canonical_name match
    exact = s.query(Vendor).filter(Vendor.canonical_name == name).first()
    if exact is not None:
        return exact

    # 2. Normalised canonical_name match
    norm = _normalize(name)
    for vendor in s.query(Vendor).all():
        if _normalize(vendor.canonical_name) == norm:
            return vendor

    # 3. aliases match (raw or normalised)
    for vendor in s.query(Vendor).all():
        aliases: list[str] = vendor.aliases or []
        if name in aliases:
            return vendor
        if any(_normalize(a) == norm for a in aliases):
            return vendor

    return None


def status_of(s: Session, name: str) -> str:
    vendor = resolve(s, name)
    if vendor is None:
        return "new"
    return vendor.status
