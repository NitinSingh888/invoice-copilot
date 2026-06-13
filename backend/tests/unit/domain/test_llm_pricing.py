from __future__ import annotations

from decimal import Decimal

from app.domain.llm_pricing import cost_usd, price_per_mtok


def test_sonnet_cost_from_tokens() -> None:
    # 1,000 input + 500 output at $3 / $15 per MTok = 0.003 + 0.0075
    assert cost_usd("anthropic", "claude-sonnet-4-6", 1000, 500) == Decimal("0.010500")


def test_haiku_is_cheaper_than_sonnet() -> None:
    haiku = cost_usd("anthropic", "claude-haiku-3-5", 10000, 10000)
    sonnet = cost_usd("anthropic", "claude-sonnet-4", 10000, 10000)
    assert haiku < sonnet


def test_openai_models_match_specific_before_generic() -> None:
    mini = price_per_mtok("openai", "gpt-4o-mini")
    full = price_per_mtok("openai", "gpt-4o")
    assert mini == (Decimal("0.15"), Decimal("0.60"))
    assert full == (Decimal("2.50"), Decimal("10"))


def test_mock_provider_is_free() -> None:
    assert cost_usd("mock", "mock", 9999, 9999) == Decimal("0.000000")
    assert price_per_mtok("mock", "anything") == (Decimal("0"), Decimal("0"))


def test_unknown_model_falls_back_to_sonnet_class() -> None:
    # Never silently under-count: unknown models price at the default (Sonnet-class).
    assert price_per_mtok("anthropic", "some-future-model") == (Decimal("3"), Decimal("15"))


def test_zero_tokens_zero_cost() -> None:
    assert cost_usd("anthropic", "claude-sonnet-4", 0, 0) == Decimal("0.000000")
