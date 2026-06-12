from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models.correction import Correction
from app.db.models.rule import Rule
from app.domain.learning.patterns import PatternCandidate, detect_pattern
from app.repositories import audit_repo, correction_repo, rule_repo


@dataclass(frozen=True)
class RuleProposal:
    candidate: PatternCandidate
    threshold_pct: Decimal
    route: str


def record_correction(
    s: Session,
    *,
    invoice_id: str,
    vendor: str,
    finding_code: str,
    user_action: str,
    over_pct: Decimal,
    reason: str | None = None,
    org_id: str | None = None,
) -> Correction:
    """Persist a user correction and return the new row."""
    corr = Correction(
        id=f"corr-{uuid4().hex[:8]}",
        invoice_id=invoice_id,
        vendor=vendor,
        finding_code=finding_code,
        user_action=user_action,
        over_pct=over_pct,
        reason=reason,
        org_id=org_id,
    )
    return correction_repo.add(s, corr)


def propose_rule(
    s: Session, vendor: str | None = None, *, org_id: str | None = None
) -> RuleProposal | None:
    """Detect a repeating correction pattern and propose a generalised rule.

    Returns None when there are not enough corrections to form a pattern.
    """
    settings = get_settings()

    raw = correction_repo.list_recent(s, org_id=org_id)
    corrections = [correction_repo.to_domain(c) for c in raw]

    # Optionally filter to a specific vendor before pattern detection.
    if vendor is not None:
        corrections = [c for c in corrections if c.vendor == vendor]

    cand = detect_pattern(corrections, settings.learn_min_corrections)
    if cand is None:
        return None

    # Generalise: round max_over_pct UP to the next whole percent.
    # e.g. max spread 0.07 → ceil(0.07 * 100) / 100 = 0.08
    raw_max = cand.max_over_pct
    threshold_pct = Decimal(math.ceil(float(raw_max) * 100)) / Decimal("100")

    # Derive route from the dominant user_action.
    action = cand.action
    route = "Priya" if action == "route" else action

    return RuleProposal(candidate=cand, threshold_pct=threshold_pct, route=route)


def activate_rule(
    s: Session,
    *,
    proposal: RuleProposal,
    threshold_pct: Decimal,
    route: str,
    created_by: str = "maya",
    reasoning: str | None = None,
    org_id: str | None = None,
) -> Rule:
    """Persist the proposed rule as an active Rule row and emit an audit event.

    If *reasoning* is supplied (e.g. from the induction agent), it is stored
    as the human-readable ``reasoning_note``; otherwise a deterministic note
    is generated from the correction data.
    """
    rule_id = f"R-{uuid4().hex[:8]}"
    cand = proposal.candidate

    if reasoning is not None:
        reasoning_note = reasoning
    else:
        reasoning_note = (
            f"Inferred from corrections at {list(cand.over_pcts)} → ~{threshold_pct}"
        )

    rule = Rule(
        id=rule_id,
        vendor=cand.vendor,
        finding_code=cand.finding_code,
        max_over_pct=threshold_pct,
        route=route,
        status="active",
        min_amount=None,
        source_correction_ids=list(cand.example_ids),
        reasoning_note=reasoning_note,
        created_by=created_by,
        org_id=org_id,
    )
    # Supersede prior active rules matching BOTH vendor AND finding_code
    # (so a vendor can have separate rules for OVER_TOLERANCE vs DUPLICATE_SUSPECT,
    # but re-approving the same (vendor, finding_code) pair disables the prior one).
    for existing in rule_repo.list_all(s, org_id=org_id):
        if (
            existing.status == "active"
            and existing.vendor == cand.vendor
            and existing.finding_code == cand.finding_code
        ):
            existing.status = "disabled"
    rule_repo.add(s, rule)

    audit_repo.append(
        s,
        actor=created_by,
        module="learning",
        action="rule_learned",
        outputs={
            "rule_id": rule_id,
            "threshold_pct": str(threshold_pct),
            "vendor": cand.vendor,
            "route": route,
        },
        org_id=org_id,
    )

    return rule


def create_rule(
    s: Session,
    *,
    vendor: str,
    finding_code: str = "OVER_TOLERANCE",
    max_over_pct: Decimal | None = None,
    min_amount: Decimal | None = None,
    route: str,
    created_by: str = "user",
    org_id: str | None = None,
) -> Rule:
    """Manually create an active Rule, superseding any prior active rule for the
    same (vendor, finding_code) pair, and emit a ``rule_created`` audit event."""
    rule_id = f"R-{uuid4().hex[:8]}"

    reasoning_note = f"Created manually by {created_by}."

    rule = Rule(
        id=rule_id,
        vendor=vendor,
        finding_code=finding_code,
        max_over_pct=max_over_pct,
        route=route,
        status="active",
        min_amount=min_amount,
        source_correction_ids=[],
        reasoning_note=reasoning_note,
        created_by=created_by,
        org_id=org_id,
    )

    # Supersede prior active rules matching BOTH vendor AND finding_code
    for existing in rule_repo.list_all(s, org_id=org_id):
        if (
            existing.status == "active"
            and existing.vendor == vendor
            and existing.finding_code == finding_code
        ):
            existing.status = "disabled"

    rule_repo.add(s, rule)

    audit_repo.append(
        s,
        actor=created_by,
        module="learning",
        action="rule_created",
        outputs={
            "rule_id": rule_id,
            "vendor": vendor,
            "finding_code": finding_code,
            "route": route,
        },
        org_id=org_id,
    )

    return rule


def set_rule_status(
    s: Session,
    rule_id: str,
    status: str,
    actor: str = "maya",
    *,
    org_id: str | None = None,
) -> Rule:
    """Change a rule's status and record a matching audit event."""
    rule = rule_repo.set_status(s, rule_id, status)

    action = "rule_disabled" if status != "active" else "rule_enabled"
    audit_repo.append(
        s,
        actor=actor,
        module="learning",
        action=action,
        outputs={"rule_id": rule_id, "status": status},
        org_id=org_id,
    )

    return rule
