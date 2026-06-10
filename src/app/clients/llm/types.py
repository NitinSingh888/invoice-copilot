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
