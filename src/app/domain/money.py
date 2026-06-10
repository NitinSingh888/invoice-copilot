from __future__ import annotations
from decimal import Decimal, ROUND_HALF_UP

CENTS = Decimal("0.01")

def to_money(value: int | str | Decimal) -> Decimal:
    """Coerce a value to a 2-dp Decimal (USD, single currency for the prototype)."""
    return Decimal(str(value)).quantize(CENTS, rounding=ROUND_HALF_UP)

def fmt_usd(amount: Decimal) -> str:
    return f"${amount:,.2f}"
