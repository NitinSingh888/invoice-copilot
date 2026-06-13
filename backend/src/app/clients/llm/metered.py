"""A pass-through ``LLMClient`` that records every call for cost/observability.

It wraps a real client and, around each method, captures token usage, latency,
the purpose, the triggering user/team, and the tagged entity, then writes one
``LlmCall`` row in its OWN short-lived transaction — so the cost is logged even
if the surrounding request later fails or rolls back. Logging never breaks the
call: failures to persist are swallowed (and logged).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from decimal import Decimal
from time import perf_counter
from typing import Any, TypeVar
from uuid import uuid4

from app.domain.llm_pricing import cost_usd

from .base import LLMClient
from .types import AgentReply, ChatMessage, CommandSpec, ExtractedInvoice
from .usage import collecting, current_entity

logger = logging.getLogger(__name__)

T = TypeVar("T")

_REASONS = {
    "extract_invoice": "Read an invoice document into structured fields",
    "converse": "Generated a conversational reply to the user",
    "parse_command": "Parsed a natural-language instruction into a command",
    "explain_rule": "Drafted a plain-language explanation of a learned rule",
}


class MeteredLLMClient:
    """Wraps an ``LLMClient``, logging each call to ``llm_calls``."""

    def __init__(
        self, inner: LLMClient, *, org_id: str | None, user_id: str | None
    ) -> None:
        self._inner = inner
        self._org_id = org_id
        self._user_id = user_id
        self.name = getattr(inner, "name", "metered")

    def _run(self, purpose: str, fn: Callable[[], T]) -> T:
        entity = current_entity()
        started = perf_counter()
        status, error = "ok", None
        with collecting() as usage:
            try:
                return fn()
            except Exception as exc:  # noqa: BLE001 - re-raised below
                status, error = "error", str(exc)[:500]
                raise
            finally:
                latency_ms = int((perf_counter() - started) * 1000)
                self._persist(purpose, usage, latency_ms, status, error, entity)

    def _persist(
        self,
        purpose: str,
        usage: list[Any],
        latency_ms: int,
        status: str,
        error: str | None,
        entity: tuple[str, str] | None,
    ) -> None:
        # Imported lazily so importing the clients package never pulls in the DB layer.
        from app.db.models.llm_call import LlmCall
        from app.db.session import SessionLocal

        try:
            provider = usage[0].provider if usage else getattr(self._inner, "name", "unknown")
            model = usage[0].model if usage else ""
            input_tokens = sum(u.input_tokens for u in usage)
            output_tokens = sum(u.output_tokens for u in usage)
            cost = cost_usd(provider, model, input_tokens, output_tokens)
            entity_type, entity_id = entity if entity else (None, None)
            with SessionLocal() as session:
                session.add(
                    LlmCall(
                        id=f"llm-{uuid4().hex[:12]}",
                        org_id=self._org_id,
                        user_id=self._user_id,
                        purpose=purpose,
                        reason=_REASONS.get(purpose, purpose),
                        entity_type=entity_type,
                        entity_id=entity_id,
                        provider=provider,
                        model=model,
                        input_tokens=int(input_tokens),
                        output_tokens=int(output_tokens),
                        cost_usd=cost,
                        latency_ms=latency_ms,
                        status=status,
                        error=error,
                    )
                )
                session.commit()
        except Exception:  # never let logging break the call
            logger.exception("Failed to record LLM call usage")

    # ----- LLMClient protocol (delegating + metered) -----------------------

    def extract_invoice(
        self, *, text: str, image_b64: str | None = None
    ) -> ExtractedInvoice:
        return self._run(
            "extract_invoice",
            lambda: self._inner.extract_invoice(text=text, image_b64=image_b64),
        )

    def converse(
        self, *, history: list[ChatMessage], context: dict[str, Any]
    ) -> AgentReply:
        return self._run("converse", lambda: self._inner.converse(history=history, context=context))

    def explain_rule(
        self,
        *,
        vendor: str,
        over_pcts: list[Decimal],
        threshold_pct: Decimal,
        route: str,
    ) -> str:
        return self._run(
            "explain_rule",
            lambda: self._inner.explain_rule(
                vendor=vendor, over_pcts=over_pcts, threshold_pct=threshold_pct, route=route
            ),
        )

    def parse_command(
        self, *, message: str, history: list[ChatMessage]
    ) -> CommandSpec:
        return self._run(
            "parse_command",
            lambda: self._inner.parse_command(message=message, history=history),
        )
