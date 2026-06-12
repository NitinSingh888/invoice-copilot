from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models.organization import Organization


def add(s: Session, org: Organization) -> Organization:
    s.add(org)
    s.flush()
    return org


def get(s: Session, org_id: str) -> Organization | None:
    return s.get(Organization, org_id)


def get_by_name(s: Session, name: str) -> Organization | None:
    return s.query(Organization).filter(Organization.name == name).first()
