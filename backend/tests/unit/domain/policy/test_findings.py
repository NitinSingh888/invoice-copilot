from app.domain.policy.findings import Severity, Finding, max_severity

def test_finding_is_frozen_value():
    f = Finding("PO_MATCH_OK", Severity.INFO, "Matched PO-1")
    assert (f.code, f.severity, f.detail) == ("PO_MATCH_OK", Severity.INFO, "Matched PO-1")

def test_max_severity_empty_is_info():
    assert max_severity([]) is Severity.INFO

def test_max_severity_picks_highest():
    findings = [
        Finding("A", Severity.INFO, ""),
        Finding("B", Severity.WARN, ""),
        Finding("C", Severity.INFO, ""),
    ]
    assert max_severity(findings) is Severity.WARN

def test_hard_stop_dominates():
    findings = [Finding("B", Severity.WARN, ""), Finding("D", Severity.HARD_STOP, "")]
    assert max_severity(findings) is Severity.HARD_STOP
