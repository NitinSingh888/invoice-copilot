"""Unit tests for induction_agent — deterministic, no network."""
from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from app.agents import induction_agent
from app.clients.llm.mock_client import MockClient
from app.db.models.correction import Correction


@pytest.fixture()
def client() -> MockClient:
    return MockClient()


# ---------------------------------------------------------------------------
# reasoning() returns a non-empty string with route and threshold
# ---------------------------------------------------------------------------


def test_reasoning_contains_route(client: MockClient) -> None:
    result = induction_agent.reasoning(
        client,
        vendor="Acme Corp",
        over_pcts=[Decimal("0.06"), Decimal("0.09")],
        threshold_pct=Decimal("0.08"),
        route="Priya",
    )
    assert "Priya" in result


def test_reasoning_contains_threshold(client: MockClient) -> None:
    result = induction_agent.reasoning(
        client,
        vendor="Acme Corp",
        over_pcts=[Decimal("0.06"), Decimal("0.09")],
        threshold_pct=Decimal("0.08"),
        route="finance_review",
    )
    # MockClient formats as "~8%" for threshold 0.08
    assert "8%" in result


def test_reasoning_returns_string(client: MockClient) -> None:
    result = induction_agent.reasoning(
        client,
        vendor="BetaCorp",
        over_pcts=[Decimal("0.05")],
        threshold_pct=Decimal("0.05"),
        route="auto_approve",
    )
    assert isinstance(result, str)
    assert len(result) > 0


def test_reasoning_is_deterministic(client: MockClient) -> None:
    r1 = induction_agent.reasoning(
        client,
        vendor="Acme",
        over_pcts=[Decimal("0.07")],
        threshold_pct=Decimal("0.08"),
        route="Priya",
    )
    r2 = induction_agent.reasoning(
        client,
        vendor="Acme",
        over_pcts=[Decimal("0.07")],
        threshold_pct=Decimal("0.08"),
        route="Priya",
    )
    assert r1 == r2


# ---------------------------------------------------------------------------
# activate_rule with reasoning= stores the note
# ---------------------------------------------------------------------------


def test_activate_rule_stores_reasoning(client: MockClient, _engine: Engine) -> None:
    from app.services import learning_service
    from app.db.models.invoice import Invoice

    TestingSession = sessionmaker(bind=_engine, expire_on_commit=False)

    with TestingSession() as s:
        # Flush invoices first so FK constraints are satisfied.
        for i in range(3):
            s.add(Invoice(id=f"inv-ind-{i}", vendor="Acme Corp", amount=Decimal("100")))
        s.flush()
        for i, over_pct in enumerate(["0.06", "0.04", "0.07"]):
            s.add(
                Correction(
                    id=f"corr-ind-{i}",
                    invoice_id=f"inv-ind-{i}",
                    vendor="Acme Corp",
                    finding_code="OVER_TOLERANCE",
                    user_action="route",
                    over_pct=Decimal(over_pct),
                )
            )
        s.commit()

    with TestingSession() as s:
        proposal = learning_service.propose_rule(s)
        assert proposal is not None

        custom_note = "Custom LLM reasoning note for the rule."
        rule = learning_service.activate_rule(
            s,
            proposal=proposal,
            threshold_pct=Decimal("0.08"),
            route="Priya",
            reasoning=custom_note,
        )
        s.commit()

        assert rule.reasoning_note == custom_note


def test_activate_rule_without_reasoning_uses_default(
    client: MockClient, _engine: Engine
) -> None:
    from app.services import learning_service
    from app.db.models.invoice import Invoice

    TestingSession = sessionmaker(bind=_engine, expire_on_commit=False)

    with TestingSession() as s:
        # Flush invoices first so FK constraints are satisfied.
        for i in range(3):
            s.add(Invoice(id=f"inv-def-{i}", vendor="Acme Corp", amount=Decimal("100")))
        s.flush()
        for i, over_pct in enumerate(["0.06", "0.04", "0.07"]):
            s.add(
                Correction(
                    id=f"corr-def-{i}",
                    invoice_id=f"inv-def-{i}",
                    vendor="Acme Corp",
                    finding_code="OVER_TOLERANCE",
                    user_action="route",
                    over_pct=Decimal(over_pct),
                )
            )
        s.commit()

    with TestingSession() as s:
        proposal = learning_service.propose_rule(s)
        assert proposal is not None

        rule = learning_service.activate_rule(
            s,
            proposal=proposal,
            threshold_pct=Decimal("0.08"),
            route="Priya",
            # reasoning omitted — uses default deterministic note
        )
        s.commit()

        assert rule.reasoning_note is not None
        assert "Inferred" in rule.reasoning_note
