"""The auto-approve policy as enforced by the deterministic guard."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.domain.decision.guard import decide
from app.domain.decision.thresholds import ConfidenceBand, Thresholds, Verdict


def _clean(**over: Any) -> dict[str, Any]:
    args: dict[str, Any] = dict(
        findings=[],
        confidence=ConfidenceBand.HIGH,
        amount=Decimal("50"),
        vendor_status="approved",
        rule_outcome=None,
        thresholds=Thresholds(t_amount=Decimal("100")),
        cold_start_ok=True,
    )
    args.update(over)
    return args


def test_clean_under_limit_auto_clears() -> None:
    assert decide(**_clean()).verdict is Verdict.AUTO_CLEAR


def test_clean_but_over_limit_escalates_with_clear_reason() -> None:
    d = decide(**_clean(amount=Decimal("250")))
    assert d.verdict is Verdict.ESCALATE
    assert "limit" in d.reason.lower()


def test_disabled_policy_never_auto_clears() -> None:
    d = decide(**_clean(thresholds=Thresholds(t_amount=Decimal("100"), auto_clear_enabled=False)))
    assert d.verdict is Verdict.ESCALATE


def test_unknown_vendor_escalates_even_when_cheap() -> None:
    # Cost is not the only gate.
    d = decide(**_clean(amount=Decimal("1"), vendor_status="new"))
    assert d.verdict is Verdict.ESCALATE
