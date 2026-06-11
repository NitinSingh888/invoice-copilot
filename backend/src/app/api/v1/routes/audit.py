from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.audit import AuditEventOut, AuditTrailOut
from app.services import audit_service

router = APIRouter()


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
