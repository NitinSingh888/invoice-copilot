from decimal import Decimal
from app.domain.money import to_money, fmt_usd

def test_to_money_parses_int_and_str():
    assert to_money(12400) == Decimal("12400")
    assert to_money("12400.50") == Decimal("12400.50")

def test_to_money_quantizes_to_cents():
    assert to_money("10.005") == Decimal("10.01")  # round half-up to cents

def test_fmt_usd():
    assert fmt_usd(Decimal("12400")) == "$12,400.00"
