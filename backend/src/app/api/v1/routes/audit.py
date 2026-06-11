from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.repositories import audit_repo
from app.schemas.audit import AuditEventOut, AuditTrailOut
from app.services import audit_service

router = APIRouter()

_GLOBAL_AUDIT_LIMIT = 100


@router.get("", response_model=AuditTrailOut)
def get_global_audit(
    db: Session = Depends(get_db),
) -> AuditTrailOut:
    """Return the most recent audit events across all invoices, newest first."""
    all_events = audit_repo.all_events(db)
    recent = list(reversed(all_events[-_GLOBAL_AUDIT_LIMIT:]))
    verified = audit_service.verify(db)
    return AuditTrailOut(
        events=[AuditEventOut.model_validate(e) for e in recent],
        chain_verified=verified,
    )


@router.get("/{invoice_id}", response_model=AuditTrailOut)
def get_audit_trail(
    invoice_id: str,
    db: Session = Depends(get_db),
) -> AuditTrailOut:
    events = audit_service.trail(db, invoice_id)
    verified = audit_service.verify(db)
    return AuditTrailOut(
        events=[AuditEventOut.model_validate(e) for e in events],
        chain_verified=verified,
    )
