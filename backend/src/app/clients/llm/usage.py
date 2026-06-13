"""LLM token-usage capture.

Real provider responses carry token counts, but the ``LLMClient`` methods return
domain objects, not usage. Rather than thread usage through every signature and
call site, each client reports usage to a context-local sink: the metering
wrapper opens a sink with ``collecting()`` around a call and reads whatever the
client recorded. ``entity_context`` lets a caller tag a call with the business
entity it's about (e.g. the invoice being extracted).
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass


@dataclass(frozen=True)
class UsageRecord:
    provider: str
    model: str
    input_tokens: int
    output_tokens: int


_sink: ContextVar[list[UsageRecord] | None] = ContextVar("llm_usage_sink", default=None)
_entity: ContextVar[tuple[str, str] | None] = ContextVar("llm_entity", default=None)


def record_usage(provider: str, model: str, input_tokens: int, output_tokens: int) -> None:
    """Report token usage for the current call, if a sink is collecting."""
    sink = _sink.get()
    if sink is not None:
        sink.append(
            UsageRecord(provider, model, int(input_tokens or 0), int(output_tokens or 0))
        )


@contextmanager
def collecting() -> Iterator[list[UsageRecord]]:
    """Collect usage reported during the block into the yielded list."""
    records: list[UsageRecord] = []
    token = _sink.set(records)
    try:
        yield records
    finally:
        _sink.reset(token)


def current_entity() -> tuple[str, str] | None:
    """The (entity_type, entity_id) tagged for the current call, if any."""
    return _entity.get()


@contextmanager
def entity_context(entity_type: str, entity_id: str) -> Iterator[None]:
    """Tag LLM calls made within the block with a business entity."""
    token = _entity.set((entity_type, entity_id))
    try:
        yield
    finally:
        _entity.reset(token)
