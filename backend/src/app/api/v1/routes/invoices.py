from __future__ import annotations

import mimetypes
import os
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.agents import extraction_agent
from app.api.deps import get_current_org, get_current_user, get_db, get_llm
from app.clients.llm.base import LLMClient
from app.clients.llm.usage import entity_context
from app.core.config import get_settings
from app.core.exceptions import AppError, NotFoundError
from app.core.paths import project_data_dir
from app.db.models.user import User
from app.domain.policy.findings import Severity
from app.domain.policy.matching import InvoiceData
from app.repositories import comment_repo, invoice_repo
from app.schemas.comment import CommentIn, CommentOut
from app.schemas.common import FindingOut
from app.schemas.invoice import (
    ActionIn,
    BulkActionIn,
    BulkActionOut,
    BulkActionResultItem,
    InvoiceIn,
    InvoiceOut,
    ProcessResultOut,
)
from app.services import enrichment_service, execution_service, learning_service, pipeline_service, policy_service

from app.core.limiter import limiter

router = APIRouter()

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB

# Directory containing the seed invoice documents (resolved for source *and*
# installed layouts). Override with IC_SAMPLE_INVOICES_DIR for alternative mounts.
_DEFAULT_SAMPLE_INVOICES_DIR = project_data_dir() / "sample_invoices"
_SAMPLE_INVOICES_DIR = Path(
    os.environ.get("IC_SAMPLE_INVOICES_DIR", str(_DEFAULT_SAMPLE_INVOICES_DIR))
)
# Directory for user-uploaded files
_UPLOADS_DIR = project_data_dir() / "uploads"


@router.post("", status_code=201, response_model=ProcessResultOut)
def create_invoice(
    body: InvoiceIn,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org),
) -> ProcessResultOut:
    invoice_id = body.id or f"inv-{uuid4().hex[:8]}"
    invoice_data = InvoiceData(
        invoice_id=invoice_id,
        vendor=body.vendor,
        amount=body.amount,
        po_number=body.po_number,
        invoice_number=body.invoice_number,
    )
    result = pipeline_service.process_invoice(db, invoice_data, body.confidence, org_id=org_id)
    inv = invoice_repo.get(db, result.invoice_id, org_id=org_id)
    if inv is None:
        raise NotFoundError(f"invoice {result.invoice_id} not found after processing")
    # Persist the source_file so the /file route can serve it for preview
    if body.source_file and not inv.source_file:
        inv.source_file = body.source_file
        db.flush()
    return ProcessResultOut(
        invoice_id=result.invoice_id,
        verdict=result.decision.verdict.value,
        route=result.decision.route,
        reason=result.decision.reason,
        status=inv.status,
        findings=[FindingOut.from_domain(f) for f in result.findings],
    )


@router.post("/upload", status_code=201, response_model=ProcessResultOut)
@limiter.limit("10/minute")
def upload_invoice(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    llm: LLMClient = Depends(get_llm),
    org_id: str = Depends(get_current_org),
) -> ProcessResultOut:
    file_bytes = file.file.read()
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise AppError(
            f"File too large ({len(file_bytes) // (1024 * 1024)}MB). Maximum is 10MB."
        )
    filename = file.filename or ""
    content_type = file.content_type or "application/octet-stream"

    invoice_id = f"inv-{uuid4().hex[:8]}"
    # Tag the extraction LLM call with the invoice it's for (cost accounting).
    with entity_context("invoice", invoice_id):
        extracted = extraction_agent.extract(
            llm,
            file_bytes=file_bytes,
            filename=filename,
            content_type=content_type,
        )

    invoice_data = InvoiceData(
        invoice_id=invoice_id,
        vendor=extracted.vendor or "",
        amount=extracted.amount or Decimal("0"),
        po_number=extracted.po_number,
        invoice_number=extracted.invoice_number or "",
    )

    result = pipeline_service.process_invoice(db, invoice_data, extracted.overall_confidence, org_id=org_id)

    inv = invoice_repo.get(db, result.invoice_id, org_id=org_id)
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
            "invoice_number": "INV/2025/NEW/0001",
            "po_number": "CUSTREF123",
            "confidence": "HIGH",
            "source_file": "AzureInterior.pdf",
        },
        {
            "label": "Over-PO escalation",
            "expected": "ESCALATE — known vendor but amount ~7 % over its PO",
            "vendor": "Coolblue B.V.",
            "amount": "717.97",
            "invoice_number": "CB-NEW-0001",
            "po_number": "12572103",
            "confidence": "HIGH",
            "source_file": "coolblue1.pdf",
        },
        {
            "label": "Unknown vendor / no PO",
            "expected": "ESCALATE — unknown vendor (new in registry), no PO referenced",
            "vendor": "OYO / Oravel Stays Private Limited",
            "amount": "1939",
            "invoice_number": "IBZY-NEW-01",
            "po_number": None,
            "confidence": "LOW",
            "source_file": "oyo.pdf",
        },
        {
            "label": "Exact duplicate",
            "expected": "BLOCK — exact duplicate of a previously cleared invoice (requires demo seed loaded)",
            "vendor": "SAECO",
            "amount": "49.99",
            "invoice_number": "VF1005193039SCONL0303006280999",  # same as cleared inv-saeco-prior
            "po_number": "SCONL000000444",
            "confidence": "MED",
            "source_file": "saeco.pdf",
        },
    ]


@router.get("", response_model=list[InvoiceOut])
def list_invoices(
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org),
) -> list[InvoiceOut]:
    return [InvoiceOut.model_validate(i) for i in invoice_repo.list_all(db, org_id=org_id)]


@router.post("/bulk-action", response_model=BulkActionOut)
def bulk_action(
    body: BulkActionIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    org_id: str = Depends(get_current_org),
) -> BulkActionOut:
    """Apply approve / hold / route to a list of invoice ids.

    Only invoices belonging to the current org are touched.
    """
    results: list[BulkActionResultItem] = []
    fields: dict[str, object] = {}
    if body.action == "route" and body.route:
        fields["route"] = body.route

    for inv_id in body.ids:
        # Verify the invoice belongs to this org before executing
        inv_check = invoice_repo.get(db, inv_id, org_id=org_id)
        if inv_check is None:
            results.append(BulkActionResultItem(id=inv_id, status="error"))
            continue
        try:
            inv = execution_service.execute(
                db, inv_id, body.action, actor=user.email, **fields
            )
            results.append(BulkActionResultItem(id=inv_id, status=inv.status))
        except (ValueError, KeyError):
            results.append(BulkActionResultItem(id=inv_id, status="error"))

    applied = sum(1 for r in results if r.status != "error")
    return BulkActionOut(applied=applied, results=results)


@router.get("/{invoice_id}/file")
def get_invoice_file(
    invoice_id: str,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org),
) -> FileResponse:
    """Return the source document for an invoice as a file download/preview."""
    inv = invoice_repo.get(db, invoice_id, org_id=org_id)
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
def get_invoice(
    invoice_id: str,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org),
) -> InvoiceOut:
    inv = invoice_repo.get(db, invoice_id, org_id=org_id)
    if inv is None:
        raise NotFoundError(f"invoice {invoice_id} not found")
    return InvoiceOut.model_validate(inv)


@router.post("/{invoice_id}/action", response_model=InvoiceOut)
def invoice_action(
    invoice_id: str,
    body: ActionIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    org_id: str = Depends(get_current_org),
) -> InvoiceOut:
    inv = invoice_repo.get(db, invoice_id, org_id=org_id)
    if inv is None:
        raise NotFoundError(f"invoice {invoice_id} not found")

    if body.action in ("route", "hold"):
        inv_domain = invoice_repo.to_domain(inv)
        enr = enrichment_service.enrich(db, inv_domain, org_id=org_id)
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
            org_id=org_id,
        )

    fields: dict[str, object] = {}
    if body.action == "edit":
        if body.amount is not None:
            fields["amount"] = body.amount
        if body.route is not None:
            fields["route"] = body.route

    # For reject, pass the mandatory reason into decision_reason.
    if body.action == "reject" and body.reason:
        fields["decision_reason"] = body.reason

    inv2 = execution_service.execute(db, invoice_id, body.action, actor=user.email, **fields)
    return InvoiceOut.model_validate(inv2)


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------


@router.post("/{invoice_id}/comments", status_code=201, response_model=CommentOut)
def add_comment(
    invoice_id: str,
    body: CommentIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    org_id: str = Depends(get_current_org),
) -> CommentOut:
    """Add a comment to an invoice.  Returns 404 when the invoice does not exist."""
    inv = invoice_repo.get(db, invoice_id, org_id=org_id)
    if inv is None:
        raise NotFoundError(f"invoice {invoice_id} not found")
    comment = comment_repo.add(db, invoice_id=invoice_id, author=user.email, body=body.body, org_id=org_id)
    return CommentOut.model_validate(comment)


@router.get("/{invoice_id}/comments", response_model=list[CommentOut])
def list_comments(
    invoice_id: str,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org),
) -> list[CommentOut]:
    """List comments for an invoice (oldest first).  Returns 404 for unknown invoices."""
    inv = invoice_repo.get(db, invoice_id, org_id=org_id)
    if inv is None:
        raise NotFoundError(f"invoice {invoice_id} not found")
    return [CommentOut.model_validate(c) for c in comment_repo.list_for_invoice(db, invoice_id, org_id=org_id)]
