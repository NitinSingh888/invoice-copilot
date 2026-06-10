from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.repositories import audit_repo, rule_repo
from app.services import learning_service


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _add_correction(
    s: Session,
    *,
    invoice_id: str,
    vendor: str = "Acme",
    finding_code: str = "OVER_TOLERANCE",
    user_action: str = "route",
    over_pct: str,
    reason: str | None = None,
) -> None:
    learning_service.record_correction(
        s,
        invoice_id=invoice_id,
        vendor=vendor,
        finding_code=finding_code,
        user_action=user_action,
        over_pct=Decimal(over_pct),
        reason=reason,
    )


# ---------------------------------------------------------------------------
# record_correction
# ---------------------------------------------------------------------------


def test_record_correction_persists_row(db: Session) -> None:
    corr = learning_service.record_correction(
        db,
        invoice_id="inv-1",
        vendor="Acme",
        finding_code="OVER_TOLERANCE",
        user_action="route",
        over_pct=Decimal("0.06"),
        reason="small overage",
    )

    assert corr.id.startswith("corr-")
    assert corr.invoice_id == "inv-1"
    assert corr.vendor == "Acme"
    assert corr.finding_code == "OVER_TOLERANCE"
    assert corr.user_action == "route"
    assert corr.over_pct == Decimal("0.06")
    assert corr.reason == "small overage"


def test_record_correction_reason_optional(db: Session) -> None:
    corr = learning_service.record_correction(
        db,
        invoice_id="inv-2",
        vendor="Acme",
        finding_code="OVER_TOLERANCE",
        user_action="approve",
        over_pct=Decimal("0.03"),
    )
    assert corr.reason is None


# ---------------------------------------------------------------------------
# propose_rule — three consistent corrections → proposal
# ---------------------------------------------------------------------------


def test_propose_rule_returns_proposal_with_ceil_threshold(db: Session) -> None:
    """3 corrections (Acme, OVER_TOLERANCE, route) with over_pcts 0.06/0.04/0.07
    → threshold_pct == 0.08 (ceil of 0.07 → next whole percent)."""
    _add_correction(db, invoice_id="i1", over_pct="0.06")
    _add_correction(db, invoice_id="i2", over_pct="0.04")
    _add_correction(db, invoice_id="i3", over_pct="0.07")

    proposal = learning_service.propose_rule(db)

    assert proposal is not None
    assert proposal.candidate.vendor == "Acme"
    assert proposal.threshold_pct == Decimal("0.08")
    assert proposal.route == "Priya"


def test_propose_rule_route_for_non_route_action(db: Session) -> None:
    """When user_action is 'approve', route should be 'approve' (not 'Priya')."""
    for i in range(3):
        learning_service.record_correction(
            db,
            invoice_id=f"inv-{i}",
            vendor="BetaCo",
            finding_code="OVER_TOLERANCE",
            user_action="approve",
            over_pct=Decimal("0.03"),
        )

    proposal = learning_service.propose_rule(db)
    assert proposal is not None
    assert proposal.route == "approve"


def test_propose_rule_too_few_corrections_returns_none(db: Session) -> None:
    """Only 2 corrections (below learn_min_corrections=3) → None."""
    _add_correction(db, invoice_id="i1", over_pct="0.06")
    _add_correction(db, invoice_id="i2", over_pct="0.04")

    assert learning_service.propose_rule(db) is None


# ---------------------------------------------------------------------------
# activate_rule — persists and emits audit
# ---------------------------------------------------------------------------


def test_activate_rule_persists_active_rule(db: Session) -> None:
    _add_correction(db, invoice_id="i1", over_pct="0.06")
    _add_correction(db, invoice_id="i2", over_pct="0.04")
    _add_correction(db, invoice_id="i3", over_pct="0.07")

    proposal = learning_service.propose_rule(db)
    assert proposal is not None

    rule = learning_service.activate_rule(
        db,
        proposal=proposal,
        threshold_pct=proposal.threshold_pct,
        route=proposal.route,
    )

    assert rule.status == "active"
    assert rule.vendor == "Acme"
    assert rule.max_over_pct == Decimal("0.08")
    assert rule.route == "Priya"

    # Should appear in list_active
    active = rule_repo.list_active(db)
    assert any(r.id == rule.id for r in active)


def test_activate_rule_writes_audit_event(db: Session) -> None:
    _add_correction(db, invoice_id="i1", over_pct="0.06")
    _add_correction(db, invoice_id="i2", over_pct="0.04")
    _add_correction(db, invoice_id="i3", over_pct="0.07")

    proposal = learning_service.propose_rule(db)
    assert proposal is not None

    rule = learning_service.activate_rule(
        db,
        proposal=proposal,
        threshold_pct=proposal.threshold_pct,
        route=proposal.route,
        created_by="maya",
    )

    events = audit_repo.all_events(db)
    rule_learned_events = [e for e in events if e.action == "rule_learned"]
    assert len(rule_learned_events) == 1
    ev = rule_learned_events[0]
    assert ev.module == "learning"
    assert ev.actor == "maya"
    assert ev.outputs is not None
    assert ev.outputs.get("rule_id") == rule.id
    assert ev.outputs.get("threshold_pct") == "0.08"


# ---------------------------------------------------------------------------
# set_rule_status
# ---------------------------------------------------------------------------


def test_set_rule_status_disables_rule(db: Session) -> None:
    _add_correction(db, invoice_id="i1", over_pct="0.06")
    _add_correction(db, invoice_id="i2", over_pct="0.04")
    _add_correction(db, invoice_id="i3", over_pct="0.07")

    proposal = learning_service.propose_rule(db)
    assert proposal is not None
    rule = learning_service.activate_rule(
        db,
        proposal=proposal,
        threshold_pct=proposal.threshold_pct,
        route=proposal.route,
    )
    rule_id = rule.id

    learning_service.set_rule_status(db, rule_id, "inactive")

    active = rule_repo.list_active(db)
    assert all(r.id != rule_id for r in active)

    events = audit_repo.all_events(db)
    disable_events = [e for e in events if e.action == "rule_disabled"]
    assert len(disable_events) == 1
    assert disable_events[0].outputs is not None
    assert disable_events[0].outputs.get("rule_id") == rule_id
