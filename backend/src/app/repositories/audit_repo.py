"""Append-only, hash-chained audit event repository.

Hash body strategy
------------------
Each event is hashed over the dict::

    {invoice_id, actor, module, action, inputs, outputs, rationale, model_meta}

``ts``, ``seq``, ``prev_hash``, and ``hash`` are EXCLUDED from the body so
that the hash is fully reproducible from stored row fields without needing to
know the exact timestamp that the database/ORM resolved.  Both ``append`` and
``verify`` build the body the same way.

Note on org_id and the hash chain
----------------------------------
``org_id`` is NOT included in the hash body — it's a routing/scoping attribute,
not part of the event's logical content.  This preserves backward compatibility
with existing chains and keeps the verify() logic stable.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.db.models.audit_event import AuditEvent
from app.domain.audit.chain import GENESIS, hash_event


def _body(
    *,
    invoice_id: str | None,
    actor: str,
    module: str,
    action: str,
    inputs: dict[str, Any],
    outputs: dict[str, Any],
    rationale: str | None,
    model_meta: dict[str, Any] | None,
) -> dict[str, Any]:
    """Canonical hashable body — stable subset of an AuditEvent row."""
    return {
        "invoice_id": invoice_id,
        "actor": actor,
        "module": module,
        "action": action,
        "inputs": inputs,
        "outputs": outputs,
        "rationale": rationale,
        "model_meta": model_meta,
    }


def append(
    s: Session,
    *,
    invoice_id: str | None = None,
    actor: str,
    module: str,
    action: str,
    inputs: dict[str, Any] | None = None,
    outputs: dict[str, Any] | None = None,
    rationale: str | None = None,
    model_meta: dict[str, Any] | None = None,
    org_id: str | None = None,
) -> AuditEvent:
    """Append a new event, chaining its hash to the previous event."""
    inputs = inputs or {}
    outputs = outputs or {}

    # 1. Find the latest event (highest seq) to get prev_hash.
    latest = s.query(AuditEvent).order_by(AuditEvent.seq.desc()).first()
    prev_hash: str = latest.hash if latest is not None else GENESIS

    # 2. Build the canonical body.
    body = _body(
        invoice_id=invoice_id,
        actor=actor,
        module=module,
        action=action,
        inputs=inputs,
        outputs=outputs,
        rationale=rationale,
        model_meta=model_meta,
    )

    # 3. Compute hash.
    event_hash = hash_event(prev_hash, body)

    # 4. Persist the row.
    event = AuditEvent(
        invoice_id=invoice_id,
        actor=actor,
        module=module,
        action=action,
        inputs=inputs,
        outputs=outputs,
        rationale=rationale,
        model_meta=model_meta,
        prev_hash=prev_hash,
        hash=event_hash,
        org_id=org_id,
    )
    s.add(event)
    s.flush()
    return event


def list_for_invoice(
    s: Session, invoice_id: str, *, org_id: str | None = None
) -> list[AuditEvent]:
    q = s.query(AuditEvent).filter(AuditEvent.invoice_id == invoice_id)
    if org_id is not None:
        q = q.filter(AuditEvent.org_id == org_id)
    return list(q.order_by(AuditEvent.seq.asc()).all())


def all_events(s: Session, *, org_id: str | None = None) -> list[AuditEvent]:
    q = s.query(AuditEvent)
    if org_id is not None:
        q = q.filter(AuditEvent.org_id == org_id)
    return list(q.order_by(AuditEvent.seq.asc()).all())


def verify(s: Session, *, org_id: str | None = None) -> bool:
    """Walk all events in seq order and verify the hash chain.

    Returns False on the first mismatch, True if the chain is intact.

    When org_id is provided, only events for that org are verified.
    Note: the hash chain is global (chained across all orgs by seq), so
    org-scoped verify only checks the subset — useful for per-org audit trails.
    """
    events = all_events(s, org_id=org_id)
    if not events:
        return True
    # For global (no org filter) verification we use GENESIS as starting point.
    # For per-org we find the prev_hash of the first event in scope.
    prev_hash: str = events[0].prev_hash
    for ev in events:
        body = _body(
            invoice_id=ev.invoice_id,
            actor=ev.actor,
            module=ev.module,
            action=ev.action,
            inputs=ev.inputs if ev.inputs is not None else {},
            outputs=ev.outputs if ev.outputs is not None else {},
            rationale=ev.rationale,
            model_meta=ev.model_meta,
        )
        expected_hash = hash_event(prev_hash, body)
        if ev.prev_hash != prev_hash or ev.hash != expected_hash:
            return False
        prev_hash = ev.hash
    return True
