from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

# Confidence level: "HIGH" | "MED" | "LOW"
Confidence = str


@dataclass(frozen=True)
class ExtractedField:
    value: str | None
    confidence: Confidence


@dataclass(frozen=True)
class ExtractedInvoice:
    vendor: str | None
    amount: Decimal | None
    po_number: str | None
    invoice_number: str | None
    fields: dict[str, ExtractedField]
    overall_confidence: Confidence


@dataclass(frozen=True)
class ChatMessage:
    role: str  # "user" | "assistant"
    content: str


@dataclass(frozen=True)
class AgentReply:
    text: str
    intent: str  # process_batch|explain|show_trail|approve|route|hold|propose_rule|smalltalk
    args: dict[str, Any] = field(default_factory=dict)


@dataclass
class CommandSpec:
    """Structured command parsed from a natural-language user message.

    action is one of:
        process | review | approve | hold | route | count | sum | smalltalk

    Filters (all optional, AND-combined when present):
      vendor       – vendor name substring to match
      amount_op    – one of "<", "<=", ">", ">=", "=="
      amount_value – the comparison value
      status       – one of: received | needs | queued | blocked | routed | held
      invoice_ref  – a specific invoice number or id

    For action=route, route_to names the person/team to route to.
    """

    action: str  # process|review|approve|hold|route|count|sum|smalltalk
    vendor: str | None = None
    amount_op: str | None = None
    amount_value: Decimal | None = None
    status: str | None = None
    invoice_ref: str | None = None
    route_to: str | None = None
