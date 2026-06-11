from decimal import Decimal
from app.domain.learning.rule_model import LearnedRule, RuleContext, apply_rules

def _rule(rid="R-7", vendor="Acme", pct="0.08", route="Priya", status="active"):
    return LearnedRule(id=rid, vendor=vendor, max_over_pct=Decimal(pct), route=route, status=status)

def test_rule_matches_vendor_and_threshold():
    ctx = RuleContext(vendor="Acme", over_pct=Decimal("0.06"))
    out = apply_rules([_rule()], ctx)
    assert out is not None and out.force_escalate and out.route == "Priya" and out.rule_id == "R-7"

def test_rule_does_not_match_above_threshold():
    ctx = RuleContext(vendor="Acme", over_pct=Decimal("0.12"))  # 12% > 8%
    assert apply_rules([_rule()], ctx) is None

def test_rule_does_not_match_other_vendor():
    ctx = RuleContext(vendor="Globex", over_pct=Decimal("0.04"))
    assert apply_rules([_rule()], ctx) is None

def test_disabled_rule_is_ignored():
    ctx = RuleContext(vendor="Acme", over_pct=Decimal("0.04"))
    assert apply_rules([_rule(status="disabled")], ctx) is None

def test_most_specific_rule_wins():
    broad = LearnedRule("R-1", vendor="Acme", max_over_pct=Decimal("0.10"), route="Priya")
    specific = LearnedRule("R-2", vendor="Acme", max_over_pct=Decimal("0.10"),
                           route="CFO", min_amount=Decimal("5000"))
    ctx = RuleContext(vendor="Acme", over_pct=Decimal("0.04"), amount=Decimal("9000"))
    out = apply_rules([broad, specific], ctx)
    assert out.rule_id == "R-2" and out.route == "CFO"
