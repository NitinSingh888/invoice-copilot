from decimal import Decimal
from app.domain.learning.patterns import Correction, detect_pattern

def _c(inv, pct):
    return Correction(invoice_id=inv, vendor="Acme", finding_code="OVER_TOLERANCE",
                      user_action="route", over_pct=Decimal(pct))

def test_three_consistent_corrections_trigger_a_candidate():
    cands = detect_pattern([_c("INV-1", "0.06"), _c("INV-2", "0.04"), _c("INV-3", "0.07")], min_count=3)
    assert cands is not None
    assert cands.vendor == "Acme" and cands.action == "route"
    assert cands.example_ids == ("INV-1", "INV-2", "INV-3")
    assert cands.max_over_pct == Decimal("0.07")  # spread upper bound, for threshold inference

def test_two_corrections_do_not_trigger():
    assert detect_pattern([_c("INV-1", "0.06"), _c("INV-2", "0.04")], min_count=3) is None

def test_inconsistent_shapes_do_not_trigger():
    mixed = [
        _c("INV-1", "0.06"),
        Correction("INV-2", "Globex", "OVER_TOLERANCE", "route", Decimal("0.04")),
        Correction("INV-3", "Acme", "OVER_TOLERANCE", "hold", Decimal("0.05")),
    ]
    assert detect_pattern(mixed, min_count=3) is None
