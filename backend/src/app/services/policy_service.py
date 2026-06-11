from __future__ import annotations

from decimal import Decimal

from app.domain.policy.checks import (
    check_duplicate,
    check_partial_po,
    check_po_match,
    check_tolerance,
    check_vendor,
)
from app.domain.policy.findings import Finding
from app.domain.policy.matching import InvoiceData
from app.services.enrichment_service import Enrichment


def run(invoice_data: InvoiceData, enr: Enrichment, tolerance_pct: Decimal) -> list[Finding]:
    findings: list[Finding] = []

    findings.append(check_po_match(invoice_data, enr.po_match))

    if enr.po_match.po is not None:
        po = enr.po_match.po
        tolerance_finding = check_tolerance(invoice_data, po, tolerance_pct)
        if tolerance_finding is not None:
            findings.append(tolerance_finding)
        partial_finding = check_partial_po(invoice_data, po)
        if partial_finding is not None:
            findings.append(partial_finding)

    vendor_finding = check_vendor(enr.vendor_status)
    if vendor_finding is not None:
        findings.append(vendor_finding)

    dup_finding = check_duplicate(invoice_data, enr.cleared_exact, enr.recent_same_amount)
    if dup_finding is not None:
        findings.append(dup_finding)

    return findings
