from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.db.models.audit_event import AuditEvent
from app.repositories import audit_repo


def record(s: Session, **event: Any) -> AuditEvent:
    return audit_repo.append(s, **event)


def trail(s: Session, invoice_id: str) -> list[AuditEvent]:
    return audit_repo.list_for_invoice(s, invoice_id)


def verify(s: Session) -> bool:
    return audit_repo.verify(s)
