from __future__ import annotations

from decimal import Decimal

from app.clients.llm.base import LLMClient


def reasoning(
    client: LLMClient,
    *,
    vendor: str,
    over_pcts: list[Decimal],
    threshold_pct: Decimal,
    route: str,
) -> str:
    """Generate a human-readable explanation for an activated rule.

    The LLM explains *why* the rule was inferred — purely informational;
    it does not execute any payment or policy decision.
    """
    return client.explain_rule(
        vendor=vendor,
        over_pcts=over_pcts,
        threshold_pct=threshold_pct,
        route=route,
    )
