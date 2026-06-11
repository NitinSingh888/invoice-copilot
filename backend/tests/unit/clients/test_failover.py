"""Tests for FailoverClient."""
from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest

from app.clients.llm.failover import FailoverClient
from app.clients.llm.mock_client import MockClient
from app.clients.llm.types import AgentReply, ChatMessage, ExtractedInvoice


class _Raises:
    """Stub client that raises on every method call."""

    name = "raises"

    def extract_invoice(
        self, *, text: str, image_b64: str | None = None
    ) -> ExtractedInvoice:
        raise RuntimeError("intentional failure")

    def converse(
        self, *, history: list[ChatMessage], context: dict[str, Any]
    ) -> AgentReply:
        raise RuntimeError("intentional failure")

    def explain_rule(
        self,
        *,
        vendor: str,
        over_pcts: list[Decimal],
        threshold_pct: Decimal,
        route: str,
    ) -> str:
        raise RuntimeError("intentional failure")


class _Canned:
    """Stub client that returns fixed predictable values."""

    name = "canned"

    def extract_invoice(
        self, *, text: str, image_b64: str | None = None
    ) -> ExtractedInvoice:
        from app.clients.llm.types import ExtractedField

        return ExtractedInvoice(
            vendor="Canned Vendor",
            amount=Decimal("42"),
            po_number="PO-CANNED",
            invoice_number="INV-CANNED",
            fields={
                "vendor": ExtractedField(value="Canned Vendor", confidence="HIGH"),
                "amount": ExtractedField(value="42", confidence="HIGH"),
                "po_number": ExtractedField(value="PO-CANNED", confidence="HIGH"),
                "invoice_number": ExtractedField(value="INV-CANNED", confidence="HIGH"),
            },
            overall_confidence="HIGH",
        )

    def converse(
        self, *, history: list[ChatMessage], context: dict[str, Any]
    ) -> AgentReply:
        return AgentReply(text="canned reply", intent="smalltalk", args={})

    def explain_rule(
        self,
        *,
        vendor: str,
        over_pcts: list[Decimal],
        threshold_pct: Decimal,
        route: str,
    ) -> str:
        return "canned explanation"


# ---------------------------------------------------------------------------
# extract_invoice failover
# ---------------------------------------------------------------------------
def test_failover_uses_canned_when_first_raises() -> None:
    client = FailoverClient([_Raises(), _Canned()])
    result = client.extract_invoice(text="any text")
    assert result.vendor == "Canned Vendor"
    assert result.amount == Decimal("42")
    assert client.last_provider == "canned"


def test_failover_uses_mock_fallback() -> None:
    text = "vendor: Acme Corp\namount: $1,000\npo: PO-1\ninvoice_number: INV-1"
    client = FailoverClient([_Raises(), MockClient()])
    result = client.extract_invoice(text=text)
    assert result.vendor == "Acme Corp"
    assert client.last_provider == "mock"


# ---------------------------------------------------------------------------
# converse failover
# ---------------------------------------------------------------------------
def test_failover_converse_canned() -> None:
    client = FailoverClient([_Raises(), _Canned()])
    reply = client.converse(
        history=[ChatMessage(role="user", content="hello")], context={}
    )
    assert reply.text == "canned reply"
    assert client.last_provider == "canned"


def test_failover_converse_mock_fallback() -> None:
    client = FailoverClient([_Raises(), MockClient()])
    reply = client.converse(
        history=[ChatMessage(role="user", content="process invoices")], context={}
    )
    assert reply.intent == "process_batch"
    assert client.last_provider == "mock"


# ---------------------------------------------------------------------------
# explain_rule failover
# ---------------------------------------------------------------------------
def test_failover_explain_rule_canned() -> None:
    client = FailoverClient([_Raises(), _Canned()])
    result = client.explain_rule(
        vendor="Acme",
        over_pcts=[Decimal("0.06")],
        threshold_pct=Decimal("0.05"),
        route="review",
    )
    assert result == "canned explanation"
    assert client.last_provider == "canned"


# ---------------------------------------------------------------------------
# first client succeeds — no fallover needed
# ---------------------------------------------------------------------------
def test_failover_first_succeeds_no_fallover() -> None:
    client = FailoverClient([_Canned(), _Raises()])
    result = client.extract_invoice(text="any text")
    assert result.vendor == "Canned Vendor"
    assert client.last_provider == "canned"


# ---------------------------------------------------------------------------
# last_provider default
# ---------------------------------------------------------------------------
def test_failover_last_provider_default() -> None:
    client = FailoverClient([_Raises(), MockClient()])
    # Before any call, last_provider defaults to the last client name
    assert client.last_provider == "mock"


# ---------------------------------------------------------------------------
# empty clients list raises
# ---------------------------------------------------------------------------
def test_failover_requires_clients() -> None:
    with pytest.raises(ValueError):
        FailoverClient([])
