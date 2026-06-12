from __future__ import annotations

from datetime import datetime, timezone
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
    "reject": "rejected",
}

_AUDIT_ACTION: dict[str, str] = {
    "approve": "executed:queued_payment",
    "edit": "executed:queued_payment",
    "route": "executed:routed",
    "hold": "executed:held",
    "reject": "executed:rejected",
}

# Human-triggered actions that should capture decision metadata.
_HUMAN_ACTIONS = frozenset({"approve", "route", "hold", "reject"})


def execute(
    s: Session,
    invoice_id: str,
    action: str,
    actor: str,
    **fields: Any,
) -> Invoice:
    """Execute a state transition on an invoice.

    For human actions (approve / route / hold / reject) the decision fields
    (decided_by, decided_at, decision_reason) are set automatically unless the
    caller passes them explicitly via **fields.
    """
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

    # Attach decision metadata for human-triggered actions.
    if action in _HUMAN_ACTIONS:
        now = datetime.now(timezone.utc)
        fields.setdefault("decided_by", actor)
        fields.setdefault("decided_at", now)
        if "decision_reason" not in fields:
            default_reason: dict[str, str] = {
                "approve": f"Approved by {actor}",
                "route": f"Routed by {actor}",
                "hold": f"Held by {actor}",
                "reject": f"Rejected by {actor}",
            }
            fields["decision_reason"] = default_reason.get(action, f"Action {action} by {actor}")

    updated = invoice_repo.set_status(s, invoice_id, target, **fields)

    audit_service.record(
        s,
        invoice_id=invoice_id,
        actor=actor,
        module="execution",
        action=_AUDIT_ACTION[action],
        outputs={"status": target, "decision_reason": fields.get("decision_reason")},
    )

    return updated
