from decimal import Decimal
from app.domain.policy.findings import Finding, Severity
from app.domain.decision.thresholds import ConfidenceBand, Verdict, Thresholds
from app.domain.decision.guard import decide, RuleOutcome

T = Thresholds(t_amount=Decimal("10000"))

def _ok_findings():
    return [Finding("PO_MATCH_OK", Severity.INFO, "")]

def test_auto_clear_happy_path():
    d = decide(findings=_ok_findings(), confidence=ConfidenceBand.HIGH,
               amount=Decimal("2000"), vendor_status="approved",
               rule_outcome=None, thresholds=T, cold_start_ok=True)
    assert d.verdict is Verdict.AUTO_CLEAR

def test_hard_stop_blocks_even_if_everything_else_ok():
    findings = [Finding("DUPLICATE_EXACT", Severity.HARD_STOP, "")]
    d = decide(findings=findings, confidence=ConfidenceBand.HIGH,
               amount=Decimal("100"), vendor_status="approved",
               rule_outcome=None, thresholds=T, cold_start_ok=True)
    assert d.verdict is Verdict.BLOCK

def test_amount_over_cap_escalates():
    d = decide(findings=_ok_findings(), confidence=ConfidenceBand.HIGH,
               amount=Decimal("12400"), vendor_status="approved",
               rule_outcome=None, thresholds=T, cold_start_ok=True)
    assert d.verdict is Verdict.ESCALATE

def test_low_confidence_escalates():
    d = decide(findings=_ok_findings(), confidence=ConfidenceBand.MED,
               amount=Decimal("100"), vendor_status="approved",
               rule_outcome=None, thresholds=T, cold_start_ok=True)
    assert d.verdict is Verdict.ESCALATE

def test_warn_finding_escalates():
    findings = [Finding("OVER_TOLERANCE", Severity.WARN, "")]
    d = decide(findings=findings, confidence=ConfidenceBand.HIGH,
               amount=Decimal("100"), vendor_status="approved",
               rule_outcome=None, thresholds=T, cold_start_ok=True)
    assert d.verdict is Verdict.ESCALATE

def test_unapproved_vendor_escalates():
    d = decide(findings=_ok_findings(), confidence=ConfidenceBand.HIGH,
               amount=Decimal("100"), vendor_status="new",
               rule_outcome=None, thresholds=T, cold_start_ok=True)
    assert d.verdict is Verdict.ESCALATE

def test_cold_start_blocks_auto_clear():
    d = decide(findings=_ok_findings(), confidence=ConfidenceBand.HIGH,
               amount=Decimal("100"), vendor_status="approved",
               rule_outcome=None, thresholds=T, cold_start_ok=False)
    assert d.verdict is Verdict.ESCALATE

def test_rule_forces_escalate_on_otherwise_auto_clearable():
    # THE precedence test: a learned rule downgrades an auto-clearable invoice.
    ro = RuleOutcome(force_escalate=True, route="Priya", rule_id="R-7")
    d = decide(findings=_ok_findings(), confidence=ConfidenceBand.HIGH,
               amount=Decimal("2000"), vendor_status="approved",
               rule_outcome=ro, thresholds=T, cold_start_ok=True)
    assert d.verdict is Verdict.ESCALATE
    assert d.route == "Priya" and "R-7" in d.reason

def test_rule_cannot_loosen_hard_stop():
    # A rule must never turn a hard-stop into anything but BLOCK.
    findings = [Finding("DUPLICATE_EXACT", Severity.HARD_STOP, "")]
    ro = RuleOutcome(force_escalate=False, route=None, rule_id="R-9")
    d = decide(findings=findings, confidence=ConfidenceBand.HIGH,
               amount=Decimal("100"), vendor_status="approved",
               rule_outcome=ro, thresholds=T, cold_start_ok=True)
    assert d.verdict is Verdict.BLOCK

def test_amount_exactly_at_cap_auto_clears():
    # The cap is inclusive (<=): an invoice exactly at T_amount still auto-clears.
    d = decide(findings=_ok_findings(), confidence=ConfidenceBand.HIGH,
               amount=Decimal("10000"), vendor_status="approved",
               rule_outcome=None, thresholds=T, cold_start_ok=True)
    assert d.verdict is Verdict.AUTO_CLEAR

def test_non_forcing_rule_is_a_noop():
    # A rule with force_escalate=False must not tighten an otherwise-auto-clearable
    # invoice — it does nothing, so the envelope still grants AUTO_CLEAR.
    ro = RuleOutcome(force_escalate=False, route="Priya", rule_id="R-1")
    d = decide(findings=_ok_findings(), confidence=ConfidenceBand.HIGH,
               amount=Decimal("2000"), vendor_status="approved",
               rule_outcome=ro, thresholds=T, cold_start_ok=True)
    assert d.verdict is Verdict.AUTO_CLEAR
