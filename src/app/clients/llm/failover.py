from __future__ import annotations

from decimal import Decimal
from typing import Any

from .base import LLMClient
from .types import AgentReply, ChatMessage, ExtractedInvoice


class FailoverClient:
    """Tries each client in order; on error continues to the next.

    The last client in the list (should be MockClient) is called without
    catching so that an error there propagates to the caller.
    ``last_provider`` is set to the name of whichever client succeeded.
    """

    name = "failover"

    def __init__(self, clients: list[LLMClient]) -> None:
        if not clients:
            raise ValueError("FailoverClient requires at least one client")
        self._clients = clients
        self.last_provider: str = clients[-1].name

    def extract_invoice(
        self, *, text: str, image_b64: str | None = None
    ) -> ExtractedInvoice:
        for i, client in enumerate(self._clients):
            is_last = i == len(self._clients) - 1
            if is_last:
                result = client.extract_invoice(text=text, image_b64=image_b64)
                self.last_provider = client.name
                return result
            try:
                result = client.extract_invoice(text=text, image_b64=image_b64)
                self.last_provider = client.name
                return result
            except Exception:
                continue
        # unreachable — loop always returns on last
        raise RuntimeError("FailoverClient: no clients available")  # pragma: no cover

    def converse(
        self, *, history: list[ChatMessage], context: dict[str, Any]
    ) -> AgentReply:
        for i, client in enumerate(self._clients):
            is_last = i == len(self._clients) - 1
            if is_last:
                result = client.converse(history=history, context=context)
                self.last_provider = client.name
                return result
            try:
                result = client.converse(history=history, context=context)
                self.last_provider = client.name
                return result
            except Exception:
                continue
        raise RuntimeError("FailoverClient: no clients available")  # pragma: no cover

    def explain_rule(
        self,
        *,
        vendor: str,
        over_pcts: list[Decimal],
        threshold_pct: Decimal,
        route: str,
    ) -> str:
        for i, client in enumerate(self._clients):
            is_last = i == len(self._clients) - 1
            if is_last:
                result = client.explain_rule(
                    vendor=vendor,
                    over_pcts=over_pcts,
                    threshold_pct=threshold_pct,
                    route=route,
                )
                self.last_provider = client.name
                return result
            try:
                result = client.explain_rule(
                    vendor=vendor,
                    over_pcts=over_pcts,
                    threshold_pct=threshold_pct,
                    route=route,
                )
                self.last_provider = client.name
                return result
            except Exception:
                continue
        raise RuntimeError("FailoverClient: no clients available")  # pragma: no cover
