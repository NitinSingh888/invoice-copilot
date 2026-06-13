"""Token → USD cost, computed from actual usage and a per-model price table.

Cost is never hard-coded per call: it's ``tokens × published price``. Prices are
USD per 1,000,000 tokens (input, output) from the providers' public pricing.
Update the table when prices change. The ``mock`` provider makes no real API call
and therefore costs nothing.
"""

from __future__ import annotations

from decimal import Decimal

# (model-name substring, input $/MTok, output $/MTok) — first match wins, so
# more specific keys (e.g. "gpt-4o-mini") must come before broader ones ("gpt-4o").
_PRICES: list[tuple[str, Decimal, Decimal]] = [
    ("claude-opus", Decimal("15"), Decimal("75")),
    ("opus", Decimal("15"), Decimal("75")),
    ("claude-haiku", Decimal("0.80"), Decimal("4")),
    ("haiku", Decimal("0.80"), Decimal("4")),
    ("claude-sonnet", Decimal("3"), Decimal("15")),
    ("sonnet", Decimal("3"), Decimal("15")),
    ("gpt-4o-mini", Decimal("0.15"), Decimal("0.60")),
    ("gpt-4o", Decimal("2.50"), Decimal("10")),
    ("gpt-4.1-mini", Decimal("0.40"), Decimal("1.60")),
    ("gpt-4.1", Decimal("2"), Decimal("8")),
]

# Fallback for an unrecognised model — assume Sonnet-class so we never silently
# under-count spend.
_DEFAULT: tuple[Decimal, Decimal] = (Decimal("3"), Decimal("15"))
_MILLION = Decimal(1_000_000)


def price_per_mtok(provider: str, model: str) -> tuple[Decimal, Decimal]:
    """(input, output) USD price per 1M tokens for a provider/model."""
    if provider == "mock":
        return Decimal("0"), Decimal("0")
    name = (model or "").lower()
    for key, p_in, p_out in _PRICES:
        if key in name:
            return p_in, p_out
    return _DEFAULT


def cost_usd(provider: str, model: str, input_tokens: int, output_tokens: int) -> Decimal:
    """Actual USD cost of a call, from its token counts. Quantised to 1e-6."""
    p_in, p_out = price_per_mtok(provider, model)
    total = (Decimal(int(input_tokens)) * p_in + Decimal(int(output_tokens)) * p_out) / _MILLION
    return total.quantize(Decimal("0.000001"))
