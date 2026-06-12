from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models.invoice import Invoice
from app.domain.decision.guard import Decision
from app.domain.decision.thresholds import Verdict
from app.domain.policy.findings import Finding
from app.domain.policy.matching import InvoiceData
from app.repositories import invoice_repo
from app.services import (
    audit_service,
    decision_service,
    enrichment_service,
    execution_service,
    policy_service,
)


@dataclass(frozen=True)
class ProcessResult:
    invoice_id: str
    decision: Decision
    findings: list[Finding]


def process_invoice(
    s: Session,
    invoice_data: InvoiceData,
    confidence: str = "HIGH",
    *,
    org_id: str | None = None,
) -> ProcessResult:
    """Run the full invoice processing pipeline for a single invoice.

    Stages
    ------
    1. Ensure the Invoice row exists (create if absent).  Audit: extraction.
    2. Enrichment — resolve vendor, match PO, check for duplicates.
    3. Policy — run all checks, collect findings.
    4. Guard — decide AUTO_CLEAR / ESCALATE / BLOCK.
    5. Persist the verdict on the Invoice row.
    6. Execute (approve) when AUTO_CLEAR; skip otherwise.
    """
    settings = get_settings()
    inv_id = invoice_data.invoice_id

    # ------------------------------------------------------------------ #
    # Stage 1 — Ensure invoice row exists                                 #
    # ------------------------------------------------------------------ #
    existing = invoice_repo.get(s, inv_id)
    if existing is None:
        invoice_repo.add(
            s,
            Invoice(
                id=inv_id,
                vendor=invoice_data.vendor,
                amount=invoice_data.amount,
                po_number=invoice_data.po_number,
                invoice_number=invoice_data.invoice_number,
                status="received",
                org_id=org_id,
            ),
        )

    audit_service.record(
        s,
        invoice_id=inv_id,
        actor="agent",
        module="extraction",
        action="extracted_fields",
        inputs={
            "vendor": invoice_data.vendor,
            "amount": str(invoice_data.amount),
            "po_number": invoice_data.po_number,
            "invoice_number": invoice_data.invoice_number,
        },
        outputs={
            "vendor": invoice_data.vendor,
            "amount": str(invoice_data.amount),
        },
        model_meta={"confidence": confidence},
        org_id=org_id,
    )

    # ------------------------------------------------------------------ #
    # Stage 2 — Enrichment                                                #
    # ------------------------------------------------------------------ #
    enr = enrichment_service.enrich(s, invoice_data, org_id=org_id)

    audit_service.record(
        s,
        invoice_id=inv_id,
        actor="agent",
        module="enrichment",
        action="resolved_vendor_matched_po",
        outputs={
            "vendor_status": enr.vendor_status,
            "po_matched": enr.po_match.po is not None,
        },
        org_id=org_id,
    )

    # ------------------------------------------------------------------ #
    # Stage 3 — Policy findings                                           #
    # ------------------------------------------------------------------ #
    findings = policy_service.run(invoice_data, enr, settings.tolerance_pct)

    audit_service.record(
        s,
        invoice_id=inv_id,
        actor="agent",
        module="policy",
        action="findings_computed",
        outputs={"findings": [f.code for f in findings]},
        org_id=org_id,
    )

    # ------------------------------------------------------------------ #
    # Stage 4 — Decision                                                  #
    # ------------------------------------------------------------------ #
    decision = decision_service.decide_invoice(s, invoice_data, enr, findings, confidence)

    audit_service.record(
        s,
        invoice_id=inv_id,
        actor="agent",
        module="guard",
        action=f"verdict:{decision.verdict.value}",
        rationale=decision.reason,
        outputs={"verdict": decision.verdict.value, "route": decision.route},
        org_id=org_id,
    )

    # ------------------------------------------------------------------ #
    # Stage 5 — Persist verdict on the Invoice row                        #
    # ------------------------------------------------------------------ #
    # Use the PO's primary key (not po_number) for the FK-constrained matched_po_id column.
    matched_po_id = enr.po_match.po.po_id if enr.po_match.po is not None else None

    if decision.verdict is Verdict.AUTO_CLEAR:
        # Status will be set to "queued" by execution_service below.
        invoice_repo.set_status(
            s,
            inv_id,
            "received",
            verdict=decision.verdict.value,
            route=decision.route,
            matched_po_id=matched_po_id,
        )
    elif decision.verdict is Verdict.ESCALATE:
        invoice_repo.set_status(
            s,
            inv_id,
            "needs",
            verdict=decision.verdict.value,
            route=decision.route,
            matched_po_id=matched_po_id,
        )
    else:  # BLOCK
        invoice_repo.set_status(
            s,
            inv_id,
            "blocked",
            verdict=decision.verdict.value,
            route=decision.route,
            matched_po_id=matched_po_id,
        )

    # ------------------------------------------------------------------ #
    # Stage 6 — Execute (auto-clear only)                                 #
    # ------------------------------------------------------------------ #
    if decision.verdict is Verdict.AUTO_CLEAR:
        execution_service.execute(s, inv_id, "approve", actor="agent")

    return ProcessResult(
        invoice_id=inv_id,
        decision=decision,
        findings=findings,
    )
