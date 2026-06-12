from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models.correction import Correction
from app.domain.learning.patterns import Correction as DomainCorrection


def add(s: Session, correction: Correction) -> Correction:
    s.add(correction)
    s.flush()
    return correction


def list_for_vendor(s: Session, vendor: str, *, org_id: str | None = None) -> list[Correction]:
    q = s.query(Correction).filter(Correction.vendor == vendor)
    if org_id is not None:
        q = q.filter(Correction.org_id == org_id)
    return list(q.all())


def list_recent(s: Session, limit: int = 50, *, org_id: str | None = None) -> list[Correction]:
    q = s.query(Correction)
    if org_id is not None:
        q = q.filter(Correction.org_id == org_id)
    return list(q.order_by(Correction.created_at.desc()).limit(limit).all())


def to_domain(c: Correction) -> DomainCorrection:
    return DomainCorrection(
        invoice_id=c.invoice_id,
        vendor=c.vendor,
        finding_code=c.finding_code,
        user_action=c.user_action,
        over_pct=c.over_pct,
    )
