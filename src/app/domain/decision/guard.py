from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from collections.abc import Sequence
from app.domain.policy.findings import Finding, Severity, max_severity
from .thresholds import ConfidenceBand, Verdict, Thresholds

@dataclass(frozen=True)
class RuleOutcome:
    """Result of evaluating learned rules. Tighten-only: may force escalation
    and set a route, but can never authorise auto-clear."""
    force_escalate: bool
    route: str | None
    rule_id: str

@dataclass(frozen=True)
class Decision:
    verdict: Verdict
    reason: str
    route: str | None = None

def decide(
    *,
    findings: Sequence[Finding],
    confidence: ConfidenceBand,
    amount: Decimal,
    vendor_status: str,
    rule_outcome: RuleOutcome | None,
    thresholds: Thresholds,
    cold_start_ok: bool,
) -> Decision:
    # 1. Hard stop — always wins, cannot be loosened by anything.
    if max_severity(findings) is Severity.HARD_STOP:
        return Decision(Verdict.BLOCK, "Hard-stop finding; never auto-paid.")

    # 2. Learned rules — tighten only (force escalate / set route).
    if rule_outcome is not None and rule_outcome.force_escalate:
        return Decision(Verdict.ESCALATE,
                        f"Learned rule {rule_outcome.rule_id} matched (rules may only tighten).",
                        route=rule_outcome.route)

    # 3. Envelope — auto-clear only if every condition holds.
    if (confidence is ConfidenceBand.HIGH
            and amount <= thresholds.t_amount
            and max_severity(findings) is Severity.INFO
            and vendor_status == "approved"
            and cold_start_ok):
        return Decision(Verdict.AUTO_CLEAR,
                        "HIGH confidence, within cap, all findings info, approved vendor → auto-clear.")

    # 4. Otherwise — hand to a human.
    return Decision(Verdict.ESCALATE, "Outside the auto-clear envelope → escalate to a human.")
