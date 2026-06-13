from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.domain.decision.guard import Decision, decide
from app.domain.decision.thresholds import ConfidenceBand, Thresholds
from app.domain.learning.rule_model import RuleContext, apply_rules
from app.domain.policy.findings import Finding
from app.domain.policy.matching import InvoiceData
from app.repositories import invoice_repo, rule_repo
from app.services.enrichment_service import Enrichment


def decide_invoice(
    s: Session,
    invoice_data: InvoiceData,
    enr: Enrichment,
    findings: list[Finding],
    confidence: str,
    *,
    org_id: str | None = None,
) -> Decision:
    settings = get_settings()

    # Auto-approve policy is per-org and editable (threshold + on/off). Falls
    # back to the global config default when the org row isn't available.
    t_amount = settings.t_amount
    auto_clear_enabled = True
    if org_id is not None:
        from app.repositories import org_repo

        org = org_repo.get(s, org_id)
        if org is not None:
            t_amount = org.auto_approve_threshold
            auto_clear_enabled = org.auto_approve_enabled

    if enr.po_match.po is not None and enr.po_match.po.amount != Decimal("0"):
        over_pct = (invoice_data.amount - enr.po_match.po.amount) / enr.po_match.po.amount
    else:
        over_pct = Decimal("0")

    rules = [rule_repo.to_domain(r) for r in rule_repo.list_active(s)]
    ctx = RuleContext(vendor=invoice_data.vendor, over_pct=over_pct, amount=invoice_data.amount)
    rule_outcome = apply_rules(rules, ctx)

    cold_start_ok = (
        invoice_repo.count_cleared_for_vendor(s, invoice_data.vendor) >= settings.cold_start_n
    )

    band = ConfidenceBand(confidence)

    return decide(
        findings=findings,
        confidence=band,
        amount=invoice_data.amount,
        vendor_status=enr.vendor_status,
        rule_outcome=rule_outcome,
        thresholds=Thresholds(t_amount=t_amount, auto_clear_enabled=auto_clear_enabled),
        cold_start_ok=cold_start_ok,
    )
