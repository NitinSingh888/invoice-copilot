from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models.rule import Rule
from app.domain.learning.rule_model import LearnedRule


def add(s: Session, rule: Rule) -> Rule:
    s.add(rule)
    s.flush()
    return rule


def get(s: Session, rule_id: str, *, org_id: str | None = None) -> Rule | None:
    r = s.get(Rule, rule_id)
    if r is None:
        return None
    if org_id is not None and r.org_id != org_id:
        return None
    return r


def list_all(s: Session, *, org_id: str | None = None) -> list[Rule]:
    q = s.query(Rule)
    if org_id is not None:
        q = q.filter(Rule.org_id == org_id)
    return list(q.all())


def list_active(s: Session, *, org_id: str | None = None) -> list[Rule]:
    q = s.query(Rule).filter(Rule.status == "active")
    if org_id is not None:
        q = q.filter(Rule.org_id == org_id)
    return list(q.all())


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
