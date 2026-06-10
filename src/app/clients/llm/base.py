from __future__ import annotations

from decimal import Decimal
from typing import Any, Protocol

from .types import AgentReply, ChatMessage, ExtractedInvoice


class LLMClient(Protocol):
    name: str

    def extract_invoice(
        self, *, text: str, image_b64: str | None = None
    ) -> ExtractedInvoice: ...

    def converse(
        self, *, history: list[ChatMessage], context: dict[str, Any]
    ) -> AgentReply: ...

    def explain_rule(
        self,
        *,
        vendor: str,
        over_pcts: list[Decimal],
        threshold_pct: Decimal,
        route: str,
    ) -> str: ...
