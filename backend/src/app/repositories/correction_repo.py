from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models.correction import Correction
from app.domain.learning.patterns import Correction as DomainCorrection


def add(s: Session, correction: Correction) -> Correction:
    s.add(correction)
    s.flush()
    return correction


def list_for_vendor(s: Session, vendor: str) -> list[Correction]:
    return list(s.query(Correction).filter(Correction.vendor == vendor).all())


def list_recent(s: Session, limit: int = 50) -> list[Correction]:
    return list(
        s.query(Correction)
        .order_by(Correction.created_at.desc())
        .limit(limit)
        .all()
    )


def to_domain(c: Correction) -> DomainCorrection:
    return DomainCorrection(
        invoice_id=c.invoice_id,
        vendor=c.vendor,
        finding_code=c.finding_code,
        user_action=c.user_action,
        over_pct=c.over_pct,
    )
