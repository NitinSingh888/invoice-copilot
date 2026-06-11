from __future__ import annotations

import mimetypes
import os
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.agents import extraction_agent
from app.api.deps import get_db, get_llm, get_role
from app.clients.llm.base import LLMClient
from app.core.config import get_settings
from app.core.exceptions import NotFoundError
from app.domain.policy.findings import Severity
from app.domain.policy.matching import InvoiceData
from app.repositories import invoice_repo
from app.schemas.common import FindingOut
from app.schemas.invoice import ActionIn, InvoiceIn, InvoiceOut, ProcessResultOut
from app.services import enrichment_service, execution_service, learning_service, pipeline_service, policy_service

router = APIRouter()

# Directory containing the seed PDFs (relative to the project root)
# File is at: backend/src/app/api/v1/routes/invoices.py
# parents[5] = backend/
_SAMPLE_INVOICES_DIR = Path(__file__).parents[5] / "data" / "sample_invoices"
# Directory for user-uploaded files
_UPLOADS_DIR = Path(__file__).parents[5] / "data" / "uploads"


@router.post("", status_code=201, response_model=ProcessResultOut)
def create_invoice(
    body: InvoiceIn,
    db: Session = Depends(get_db),
) -> ProcessResultOut:
    invoice_id = body.id or f"inv-{uuid4().hex[:8]}"
    invoice_data = InvoiceData(
        invoice_id=invoice_id,
        vendor=body.vendor,
        amount=body.amount,
        po_number=body.po_number,
        invoice_number=body.invoice_number,
    )
    result = pipeline_service.process_invoice(db, invoice_data, body.confidence)
    inv = invoice_repo.get(db, result.invoice_id)
    if inv is None:
        raise NotFoundError(f"invoice {result.invoice_id} not found after processing")
    return ProcessResultOut(
        invoice_id=result.invoice_id,
        verdict=result.decision.verdict.value,
        route=result.decision.route,
        reason=result.decision.reason,
        status=inv.status,
        findings=[FindingOut.from_domain(f) for f in result.findings],
    )


@router.post("/upload", status_code=201, response_model=ProcessResultOut)
def upload_invoice(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    role: str = Depends(get_role),
    llm: LLMClient = Depends(get_llm),
) -> ProcessResultOut:
    file_bytes = file.file.read()
    filename = file.filename or ""
    content_type = file.content_type or "application/octet-stream"

    extracted = extraction_agent.extract(
        llm,
        file_bytes=file_bytes,
        filename=filename,
        content_type=content_type,
    )

    invoice_id = f"inv-{uuid4().hex[:8]}"
    invoice_data = InvoiceData(
        invoice_id=invoice_id,
        vendor=extracted.vendor or "",
        amount=extracted.amount or Decimal("0"),
        po_number=extracted.po_number,
        invoice_number=extracted.invoice_number or "",
    )

    result = pipeline_service.process_invoice(db, invoice_data, extracted.overall_confidence)

    inv = invoice_repo.get(db, result.invoice_id)
    if inv is None:
        raise NotFoundError(f"invoice {result.invoice_id} not found after processing")

    # Persist the uploaded file so it can be previewed later
    if file_bytes:
        ext = Path(filename).suffix if filename else ""
        _UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        stored_name = f"{invoice_id}{ext}"
        stored_path = _UPLOADS_DIR / stored_name
        stored_path.write_bytes(file_bytes)
        inv.source_file = str(stored_path)
        db.flush()

    return ProcessResultOut(
        invoice_id=result.invoice_id,
        verdict=result.decision.verdict.value,
        route=result.decision.route,
        reason=result.decision.reason,
        status=inv.status,
        findings=[FindingOut.from_domain(f) for f in result.findings],
    )


@router.get("/samples")
def get_sample_invoices() -> list[dict[str, object]]:
    """Return ~4 ready-to-POST sample invoices (InvoiceIn-shaped) covering
    each interesting pipeline outcome.  Use these to demo the upload UI before
    the user has real invoices.

    Each sample has ``label`` and ``expected`` hint fields (extra, not part of
    InvoiceIn) so the frontend can display context.

    Note: sample (d) produces DUPLICATE_EXACT only when the demo seed has been
    loaded (so the prior cleared SAECO invoice exists in the DB).
    """
    return [
        {
            "label": "Clean auto-clear",
            "expected": "AUTO_CLEAR — approved vendor, amount matches PO exactly",
            "vendor": "Azure Interior",
            "amount": "279.84",
            "invoice_number": "INV-9001",
            "po_number": "CUSTREF123",
            "confidence": "HIGH",
        },
        {
            "label": "Over-PO escalation",
            "expected": "ESCALATE — known vendor but amount ~7 % over its PO",
            "vendor": "Coolblue B.V.",
            "amount": "767.23",  # ~14 % over PO-12572103 (670.99)
            "invoice_number": "INV-9002",
            "po_number": "12572103",
            "confidence": "HIGH",
        },
        {
            "label": "Unknown vendor / no PO",
            "expected": "ESCALATE — vendor not in registry, no PO referenced",
            "vendor": "Phantom Supplies Inc",
            "amount": "4750",
            "invoice_number": "INV-9003",
            "po_number": None,
            "confidence": "MED",
        },
        {
            "label": "Exact duplicate",
            "expected": "BLOCK — exact duplicate of a previously cleared invoice (requires demo seed loaded)",
            "vendor": "SAECO",
            "amount": "49.99",
            "invoice_number": "VF1005193039SCONL0303006280999",  # same as cleared inv-saeco-prior
            "po_number": "SCONL000000444",
            "confidence": "MED",
        },
    ]


@router.get("", response_model=list[InvoiceOut])
def list_invoices(db: Session = Depends(get_db)) -> list[InvoiceOut]:
    return [InvoiceOut.model_validate(i) for i in invoice_repo.list_all(db)]


@router.get("/{invoice_id}/file")
def get_invoice_file(invoice_id: str, db: Session = Depends(get_db)) -> FileResponse:
    """Return the source document for an invoice as a file download/preview.

    For seed invoices the file is served from ``data/sample_invoices/<source_file>``.
    For uploaded invoices the stored path is used directly (absolute path saved at
    upload time).  Returns 404 if no file is associated with the invoice.
    """
    inv = invoice_repo.get(db, invoice_id)
    if inv is None:
        raise NotFoundError(f"invoice {invoice_id} not found")

    source = inv.source_file
    if not source:
        raise NotFoundError(f"invoice {invoice_id} has no associated file")

    # Absolute path — uploaded files are stored as absolute paths
    if os.path.isabs(source):
        file_path = Path(source)
    else:
        # Relative filename — look up in the seed sample_invoices directory
        file_path = _SAMPLE_INVOICES_DIR / source

    if not file_path.exists():
        raise NotFoundError(f"file for invoice {invoice_id} not found on disk")

    media_type, _ = mimetypes.guess_type(str(file_path))
    if media_type is None:
        media_type = "application/octet-stream"

    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=file_path.name,
        # inline so the browser renders it in the preview iframe instead of downloading
        content_disposition_type="inline",
    )


@router.get("/{invoice_id}", response_model=InvoiceOut)
def get_invoice(invoice_id: str, db: Session = Depends(get_db)) -> InvoiceOut:
    inv = invoice_repo.get(db, invoice_id)
    if inv is None:
        raise NotFoundError(f"invoice {invoice_id} not found")
    return InvoiceOut.model_validate(inv)


@router.post("/{invoice_id}/action", response_model=InvoiceOut)
def invoice_action(
    invoice_id: str,
    body: ActionIn,
    db: Session = Depends(get_db),
    role: str = Depends(get_role),
) -> InvoiceOut:
    inv = invoice_repo.get(db, invoice_id)
    if inv is None:
        raise NotFoundError(f"invoice {invoice_id} not found")

    if body.action in ("route", "hold"):
        inv_domain = invoice_repo.to_domain(inv)
        enr = enrichment_service.enrich(db, inv_domain)
        settings = get_settings()
        findings = policy_service.run(inv_domain, enr, settings.tolerance_pct)

        # Pick first WARN finding code; fall back to "MANUAL"
        warn_finding = next(
            (f for f in findings if f.severity is Severity.WARN), None
        )
        finding_code = warn_finding.code if warn_finding is not None else "MANUAL"

        # Compute over_pct from matched PO if available
        if enr.po_match.po is not None:
            po_amount = enr.po_match.po.amount
            over_pct = (inv_domain.amount - po_amount) / po_amount if po_amount else Decimal("0")
        else:
            over_pct = Decimal("0")

        learning_service.record_correction(
            db,
            invoice_id=invoice_id,
            vendor=inv.vendor or "",
            finding_code=finding_code,
            user_action=body.action,
            over_pct=over_pct,
            reason=body.reason,
        )

    fields: dict[str, object] = {}
    if body.action == "edit":
        if body.amount is not None:
            fields["amount"] = body.amount
        if body.route is not None:
            fields["route"] = body.route

    inv2 = execution_service.execute(db, invoice_id, body.action, actor=role, **fields)
    return InvoiceOut.model_validate(inv2)
