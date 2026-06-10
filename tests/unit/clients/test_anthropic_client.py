"""Tests for AnthropicClient — no real network calls."""
from __future__ import annotations

import json
from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock

import pytest

from app.clients.llm.anthropic_client import AnthropicClient


def _make_canned_response(text: str) -> MagicMock:
    """Build a fake anthropic Message whose first content block has .text."""
    block = MagicMock()
    block.text = text
    response = MagicMock()
    response.content = [block]
    return response


@pytest.fixture()
def client() -> AnthropicClient:
    return AnthropicClient(api_key="test-key", model="claude-3-5-sonnet-latest")


def _prime_client(client: AnthropicClient, canned_text: str) -> None:
    """Ensure the internal _client is initialised and its messages.create is patched."""
    # Force lazy init with a mock so we never hit the network
    mock_sdk = MagicMock()
    mock_sdk.messages.create.return_value = _make_canned_response(canned_text)
    client._client = mock_sdk  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# extract_invoice
# ---------------------------------------------------------------------------
EXTRACT_JSON = json.dumps(
    {
        "vendor": "Acme Corp",
        "amount": "9800",
        "po_number": "PO-1",
        "invoice_number": "A-1",
        "confidence": "HIGH",
    }
)


def test_extract_invoice_parses_json(client: AnthropicClient) -> None:
    _prime_client(client, EXTRACT_JSON)
    result = client.extract_invoice(text="invoice text")
    assert result.vendor == "Acme Corp"
    assert result.amount == Decimal("9800")
    assert result.po_number == "PO-1"
    assert result.invoice_number == "A-1"
    assert result.overall_confidence == "HIGH"


def test_extract_invoice_calls_messages_create(client: AnthropicClient) -> None:
    _prime_client(client, EXTRACT_JSON)
    client.extract_invoice(text="some text")
    client._client.messages.create.assert_called_once()  # type: ignore[attr-defined]


def test_extract_invoice_sdk_error_returns_fallback(client: AnthropicClient) -> None:
    mock_sdk = MagicMock()
    mock_sdk.messages.create.side_effect = RuntimeError("network error")
    client._client = mock_sdk  # type: ignore[attr-defined]

    result = client.extract_invoice(text="some text")
    assert result.overall_confidence == "LOW"
    assert result.vendor is None
    assert result.amount is None


def test_extract_invoice_bad_json_returns_fallback(client: AnthropicClient) -> None:
    _prime_client(client, "not valid json at all")
    result = client.extract_invoice(text="some text")
    assert result.overall_confidence == "LOW"


def test_extract_invoice_with_image_b64(client: AnthropicClient) -> None:
    _prime_client(client, EXTRACT_JSON)
    result = client.extract_invoice(text="", image_b64="fake_base64_data")
    # Should parse successfully; the image block is included in the call
    assert result.vendor == "Acme Corp"
    call_args: Any = client._client.messages.create.call_args  # type: ignore[attr-defined]
    # Check that the content list contains an image block
    messages_arg = call_args.kwargs.get("messages") or call_args[1].get("messages", [])
    content_blocks = messages_arg[0]["content"]
    types = [b.get("type") if isinstance(b, dict) else b["type"] for b in content_blocks]
    assert "image" in types


def test_extract_missing_fields_low_confidence(client: AnthropicClient) -> None:
    partial = json.dumps({"vendor": "Acme", "confidence": "MED"})
    _prime_client(client, partial)
    result = client.extract_invoice(text="text")
    # amount, po_number, invoice_number are missing → overall LOW
    assert result.overall_confidence == "LOW"


# ---------------------------------------------------------------------------
# converse
# ---------------------------------------------------------------------------
CONVERSE_JSON = json.dumps(
    {"text": "Starting batch run.", "intent": "process_batch", "args": {}}
)


def test_converse_parses_intent(client: AnthropicClient) -> None:
    from app.clients.llm.types import ChatMessage

    _prime_client(client, CONVERSE_JSON)
    reply = client.converse(
        history=[ChatMessage(role="user", content="run the batch")], context={}
    )
    assert reply.intent == "process_batch"
    assert "batch" in reply.text.lower()


def test_converse_sdk_error_returns_smalltalk(client: AnthropicClient) -> None:
    from app.clients.llm.types import ChatMessage

    mock_sdk = MagicMock()
    mock_sdk.messages.create.side_effect = RuntimeError("error")
    client._client = mock_sdk  # type: ignore[attr-defined]

    reply = client.converse(history=[ChatMessage(role="user", content="hello")], context={})
    assert reply.intent == "smalltalk"
