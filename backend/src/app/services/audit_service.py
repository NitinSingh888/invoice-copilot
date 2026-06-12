from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.db.models.audit_event import AuditEvent
from app.repositories import audit_repo


def record(s: Session, *, org_id: str | None = None, **event: Any) -> AuditEvent:
    return audit_repo.append(s, org_id=org_id, **event)


def trail(s: Session, invoice_id: str, *, org_id: str | None = None) -> list[AuditEvent]:
    return audit_repo.list_for_invoice(s, invoice_id, org_id=org_id)


def verify(s: Session, *, org_id: str | None = None) -> bool:
    return audit_repo.verify(s, org_id=org_id)
