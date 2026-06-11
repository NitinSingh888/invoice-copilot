"""Tests for MockClient — fully deterministic, no network calls."""
from __future__ import annotations

from decimal import Decimal

import pytest

from app.clients.llm.mock_client import MockClient
from app.clients.llm.types import ChatMessage


@pytest.fixture()
def client() -> MockClient:
    return MockClient()


# ---------------------------------------------------------------------------
# extract_invoice
# ---------------------------------------------------------------------------
FULL_TEXT = "vendor: Acme Corp\namount: $9,800\npo: PO-1\ninvoice_number: A-1"


def test_extract_full(client: MockClient) -> None:
    result = client.extract_invoice(text=FULL_TEXT)
    assert result.vendor == "Acme Corp"
    assert result.amount == Decimal("9800")
    assert result.po_number == "PO-1"
    assert result.invoice_number == "A-1"
    assert result.overall_confidence == "HIGH"


def test_extract_deterministic(client: MockClient) -> None:
    """Calling twice yields equal results."""
    r1 = client.extract_invoice(text=FULL_TEXT)
    r2 = client.extract_invoice(text=FULL_TEXT)
    assert r1 == r2


def test_extract_missing_amount_is_low(client: MockClient) -> None:
    text = "vendor: Acme Corp\npo: PO-1\ninvoice_number: A-1"
    result = client.extract_invoice(text=text)
    assert result.overall_confidence == "LOW"
    assert result.amount is None


def test_extract_all_missing_is_low(client: MockClient) -> None:
    result = client.extract_invoice(text="nothing useful here")
    assert result.overall_confidence == "LOW"
    assert result.vendor is None
    assert result.amount is None


def test_extract_image_b64_ignored_gracefully(client: MockClient) -> None:
    """image_b64 is accepted but mock ignores it; still deterministic."""
    r1 = client.extract_invoice(text=FULL_TEXT, image_b64=None)
    r2 = client.extract_invoice(text=FULL_TEXT, image_b64="fake_b64_data")
    assert r1.vendor == r2.vendor
    assert r1.amount == r2.amount


# ---------------------------------------------------------------------------
# converse — intent routing
# ---------------------------------------------------------------------------
def _msg(content: str) -> list[ChatMessage]:
    return [ChatMessage(role="user", content=content)]


def test_converse_process_batch(client: MockClient) -> None:
    reply = client.converse(history=_msg("process invoices today"), context={})
    assert reply.intent == "process_batch"


def test_converse_process_go_ahead(client: MockClient) -> None:
    reply = client.converse(history=_msg("go ahead and run"), context={})
    assert reply.intent == "process_batch"


def test_converse_explain_why(client: MockClient) -> None:
    reply = client.converse(history=_msg("why was this invoice escalated?"), context={})
    assert reply.intent == "explain"


def test_converse_explain_inv_id_captured(client: MockClient) -> None:
    reply = client.converse(history=_msg("explain INV-4495 please"), context={})
    assert reply.intent == "explain"
    assert reply.args.get("invoice_id") == "INV-4495"


def test_converse_explain_cyberdyne(client: MockClient) -> None:
    reply = client.converse(history=_msg("what about cyberdyne?"), context={})
    assert reply.intent == "explain"


def test_converse_approve(client: MockClient) -> None:
    reply = client.converse(history=_msg("approve INV-001"), context={})
    assert reply.intent == "approve"
    assert reply.args.get("invoice_id") == "INV-001"


def test_converse_route(client: MockClient) -> None:
    reply = client.converse(history=_msg("route this invoice"), context={})
    assert reply.intent == "route"


def test_converse_hold(client: MockClient) -> None:
    reply = client.converse(history=_msg("hold INV-007"), context={})
    assert reply.intent == "hold"
    assert reply.args.get("invoice_id") == "INV-007"


def test_converse_propose_rule(client: MockClient) -> None:
    reply = client.converse(history=_msg("learn a new rule from this"), context={})
    assert reply.intent == "propose_rule"


def test_converse_smalltalk_hello(client: MockClient) -> None:
    reply = client.converse(history=_msg("hello"), context={})
    assert reply.intent == "smalltalk"


def test_converse_smalltalk_no_args(client: MockClient) -> None:
    reply = client.converse(history=_msg("hello there"), context={})
    assert reply.intent == "smalltalk"
    assert reply.args == {}


# ---------------------------------------------------------------------------
# explain_rule
# ---------------------------------------------------------------------------
def test_explain_rule_contains_pct(client: MockClient) -> None:
    result = client.explain_rule(
        vendor="Acme",
        over_pcts=[Decimal("0.06"), Decimal("0.09")],
        threshold_pct=Decimal("0.08"),
        route="finance_review",
    )
    assert "~8%" in result
    assert "finance_review" in result
    assert "Acme" in result


def test_explain_rule_format(client: MockClient) -> None:
    result = client.explain_rule(
        vendor="BetaCorp",
        over_pcts=[Decimal("0.10")],
        threshold_pct=Decimal("0.05"),
        route="auto_approve",
    )
    assert "~5%" in result
    assert "BetaCorp" in result
    assert "10%" in result
