from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from collections.abc import Sequence
from app.domain.decision.guard import RuleOutcome

@dataclass(frozen=True)
class LearnedRule:
    id: str
    vendor: str | None
    max_over_pct: Decimal | None
    route: str
    status: str = "active"
    min_amount: Decimal | None = None

    @property
    def specificity(self) -> int:
        return sum(c is not None for c in (self.vendor, self.max_over_pct, self.min_amount))

@dataclass(frozen=True)
class RuleContext:
    vendor: str
    over_pct: Decimal
    amount: Decimal | None = None

def _matches(rule: LearnedRule, ctx: RuleContext) -> bool:
    if rule.status != "active":
        return False
    if rule.vendor is not None and rule.vendor != ctx.vendor:
        return False
    if rule.max_over_pct is not None and ctx.over_pct >= rule.max_over_pct:
        return False
    if rule.min_amount is not None and (ctx.amount is None or ctx.amount < rule.min_amount):
        return False
    return True

def apply_rules(rules: Sequence[LearnedRule], ctx: RuleContext) -> RuleOutcome | None:
    matching = [r for r in rules if _matches(r, ctx)]
    if not matching:
        return None
    # Most-specific wins; tie-break by id so the winner is deterministic
    # regardless of input order.
    winner = max(matching, key=lambda r: (r.specificity, r.id))
    return RuleOutcome(force_escalate=True, route=winner.route, rule_id=winner.id)
