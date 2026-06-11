from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models.rule import Rule
from app.domain.learning.rule_model import LearnedRule


def add(s: Session, rule: Rule) -> Rule:
    s.add(rule)
    s.flush()
    return rule


def get(s: Session, rule_id: str) -> Rule | None:
    return s.get(Rule, rule_id)


def list_all(s: Session) -> list[Rule]:
    return list(s.query(Rule).all())


def list_active(s: Session) -> list[Rule]:
    return list(s.query(Rule).filter(Rule.status == "active").all())


def set_status(s: Session, rule_id: str, status: str) -> Rule:
    rule = s.get(Rule, rule_id)
    if rule is None:
        raise ValueError(f"Rule {rule_id!r} not found")
    rule.status = status
    s.flush()
    return rule


def to_domain(rule: Rule) -> LearnedRule:
    return LearnedRule(
        id=rule.id,
        vendor=rule.vendor,
        max_over_pct=rule.max_over_pct,
        route=rule.route,
        status=rule.status,
        min_amount=rule.min_amount,
    )
