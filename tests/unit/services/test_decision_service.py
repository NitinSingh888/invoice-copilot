from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.db.models.invoice import Invoice
from app.db.models.rule import Rule
from app.db.models.vendor import Vendor
from app.domain.decision.thresholds import Verdict
from app.domain.policy.findings import Finding, Severity
from app.domain.policy.matching import InvoiceData, POMatch, PurchaseOrder
from app.repositories import invoice_repo, rule_repo, vendor_repo
from app.services.decision_service import decide_invoice
from app.services.enrichment_service import Enrichment


def _inv_data(
    vendor: str = "Acme Corp",
    amount: str = "5000.00",
    invoice_number: str = "INV-001",
    po_number: str | None = "PO-1",
) -> InvoiceData:
    return InvoiceData(
        invoice_id="inv-1",
        vendor=vendor,
        amount=Decimal(amount),
        po_number=po_number,
        invoice_number=invoice_number,
    )


def _po(amount: str = "5000.00") -> PurchaseOrder:
    return PurchaseOrder(po_number="PO-1", vendor="Acme Corp", amount=Decimal(amount))


def _clean_findings() -> list[Finding]:
    return [Finding("PO_MATCH_OK", Severity.INFO, "Matched PO-1")]


def _hard_stop_findings() -> list[Finding]:
    return [Finding("DUPLICATE_EXACT", Severity.HARD_STOP, "Already cleared")]


def _seed_approved_vendor(db: Session, name: str = "Acme Corp") -> None:
    vendor_repo.add(db, Vendor(id="v1", canonical_name=name, status="approved"))


def _seed_cleared_invoices(db: Session, vendor: str, count: int) -> None:
    for i in range(count):
        invoice_repo.add(
            db,
            Invoice(
                id=f"past-inv-{i}",
                status="cleared",
                vendor=vendor,
                amount=Decimal("1000.00"),
                invoice_number=f"HIST-{i}",
            ),
        )


def test_auto_clear_when_all_conditions_met(db: Session) -> None:
    _seed_approved_vendor(db)
    _seed_cleared_invoices(db, "Acme Corp", 2)  # cold_start_n=2

    enr = Enrichment(
        vendor_status="approved",
        po_match=POMatch(po=_po()),
        cleared_exact=[],
        recent_same_amount=[],
    )
    decision = decide_invoice(db, _inv_data(), enr, _clean_findings(), "HIGH")
    assert decision.verdict == Verdict.AUTO_CLEAR


def test_escalate_under_cold_start(db: Session) -> None:
    _seed_approved_vendor(db)
    # Seed only 1 cleared invoice (cold_start_n=2 → not met)
    _seed_cleared_invoices(db, "Acme Corp", 1)

    enr = Enrichment(
        vendor_status="approved",
        po_match=POMatch(po=_po()),
        cleared_exact=[],
        recent_same_amount=[],
    )
    decision = decide_invoice(db, _inv_data(), enr, _clean_findings(), "HIGH")
    assert decision.verdict == Verdict.ESCALATE


def test_escalate_with_route_when_rule_matches(db: Session) -> None:
    _seed_approved_vendor(db)
    _seed_cleared_invoices(db, "Acme Corp", 2)

    # Rule: Acme + max_over_pct=0.20 → rule matches when over_pct < 0.20
    # (the rule fires/escalates when over_pct is within the rule's threshold)
    rule_repo.add(
        db,
        Rule(
            id="rule-acme",
            vendor="Acme Corp",
            max_over_pct=Decimal("0.20"),
            route="finance-team",
            status="active",
        ),
    )

    # Invoice 10% over PO → over_pct=0.10 < 0.20 → rule matches → force_escalate
    inv = _inv_data(amount="5500.00")
    po = _po(amount="5000.00")
    enr = Enrichment(
        vendor_status="approved",
        po_match=POMatch(po=po),
        cleared_exact=[],
        recent_same_amount=[],
    )
    decision = decide_invoice(db, inv, enr, _clean_findings(), "HIGH")
    assert decision.verdict == Verdict.ESCALATE
    assert decision.route == "finance-team"


def test_block_on_hard_stop_finding(db: Session) -> None:
    _seed_approved_vendor(db)
    _seed_cleared_invoices(db, "Acme Corp", 2)

    enr = Enrichment(
        vendor_status="approved",
        po_match=POMatch(po=_po()),
        cleared_exact=[],
        recent_same_amount=[],
    )
    decision = decide_invoice(db, _inv_data(), enr, _hard_stop_findings(), "HIGH")
    assert decision.verdict == Verdict.BLOCK


def test_escalate_low_confidence(db: Session) -> None:
    _seed_approved_vendor(db)
    _seed_cleared_invoices(db, "Acme Corp", 2)

    enr = Enrichment(
        vendor_status="approved",
        po_match=POMatch(po=_po()),
        cleared_exact=[],
        recent_same_amount=[],
    )
    decision = decide_invoice(db, _inv_data(), enr, _clean_findings(), "LOW")
    assert decision.verdict == Verdict.ESCALATE


def test_escalate_above_amount_cap(db: Session) -> None:
    _seed_approved_vendor(db)
    _seed_cleared_invoices(db, "Acme Corp", 2)

    enr = Enrichment(
        vendor_status="approved",
        po_match=POMatch(po=_po(amount="15000.00")),
        cleared_exact=[],
        recent_same_amount=[],
    )
    # amount=15000 > t_amount=10000 → cannot auto-clear
    inv = _inv_data(amount="15000.00")
    decision = decide_invoice(db, inv, enr, _clean_findings(), "HIGH")
    assert decision.verdict == Verdict.ESCALATE
