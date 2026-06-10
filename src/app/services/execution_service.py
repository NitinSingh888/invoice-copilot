from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.db.models.invoice import Invoice
from app.repositories import invoice_repo
from app.services import audit_service

TERMINAL: dict[str, str] = {
    "approve": "queued",
    "edit": "queued",
    "route": "routed",
    "hold": "held",
}

_AUDIT_ACTION: dict[str, str] = {
    "approve": "executed:queued_payment",
    "edit": "executed:queued_payment",
    "route": "executed:routed",
    "hold": "executed:held",
}


def execute(
    s: Session,
    invoice_id: str,
    action: str,
    actor: str,
    **fields: Any,
) -> Invoice:
    inv = invoice_repo.get(s, invoice_id)
    if inv is None:
        raise ValueError(f"Invoice {invoice_id!r} not found")

    target = TERMINAL[action]

    if inv.status == target:
        audit_service.record(
            s,
            invoice_id=invoice_id,
            actor=actor,
            module="execution",
            action="execute:noop",
            rationale="idempotent no-op",
        )
        return inv

    updated = invoice_repo.set_status(s, invoice_id, target, **fields)

    audit_service.record(
        s,
        invoice_id=invoice_id,
        actor=actor,
        module="execution",
        action=_AUDIT_ACTION[action],
        outputs={"status": target},
    )

    return updated
