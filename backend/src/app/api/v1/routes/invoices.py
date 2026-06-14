from __future__ import annotations

import mimetypes
import os
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.responses import FileResponse, Response
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
@limiter.limit("30/minute")
def create_invoice(
    request: Request,
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
    # Persist the source_file for preview.  When S3 is enabled and the
    # source_file names a local sample PDF, upload it to S3 automatically.
    if body.source_file and not inv.source_file:
        from app.clients import s3

        if s3.is_enabled():
            local_path = _SAMPLE_INVOICES_DIR / body.source_file
            if local_path.exists():
                ext = local_path.suffix
                key = s3.make_key(org_id, invoice_id, ext)
                s3.upload(local_path.read_bytes(), key)
                inv.source_file = f"s3://{key}"
            else:
                inv.source_file = body.source_file
        else:
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
    file_bytes = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise AppError(
            "File too large. Maximum is 10MB."
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

    # Persist the uploaded file for later preview
    if file_bytes:
        ext = Path(filename).suffix if filename else ""
        from app.clients import s3

        if s3.is_enabled():
            key = s3.make_key(org_id, invoice_id, ext)
            s3.upload(file_bytes, key, content_type)
            inv.source_file = f"s3://{key}"
        else:
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
    """Return 100 real invoice samples with PDFs hosted on S3.

    Loaded from data/real_samples.json (generated by scripts/upload_sample_invoices.py).
    Each sample has a source_file pointing to an S3 key so the PDF preview works.
    """
    return _load_real_samples()


_real_samples_cache: list[dict[str, object]] | None = None


def _load_real_samples() -> list[dict[str, object]]:
    """Load real invoice samples from data/real_samples.json (cached)."""
    global _real_samples_cache
    if _real_samples_cache is not None:
        return _real_samples_cache
    import json

    samples_path = project_data_dir() / "real_samples.json"
    if samples_path.exists():
        _real_samples_cache = json.loads(samples_path.read_text())
        return _real_samples_cache
    return []


# Legacy function kept for backward compat with tests
def _generate_samples() -> list[dict[str, object]]:
    """Fallback: build samples from seed data if real_samples.json is missing."""
    import hashlib

    # ---- vendor + PO catalog (mirrors seed.py) ----
    approved_with_po: list[dict[str, str]] = [
        {"vendor": "Azure Interior", "po": "CUSTREF123", "po_amt": "279.84"},
        {"vendor": "WS Retail Services Pvt. Ltd", "po": "OD304175096047380001", "po_amt": "319.00"},
        {"vendor": "NETPRESSE", "po": "365146", "po_amt": "56.02"},
        {"vendor": "QualityHosting AG", "po": "CON02858", "po_amt": "34.73"},
        {"vendor": "Klein and Sons", "po": "PO-KLEIN-3290", "po_amt": "3.29"},
        {"vendor": "Herrera PLC", "po": "PO-HERRERA-1645", "po_amt": "16.45"},
        {"vendor": "Tran, Hurst and Rodgers", "po": "PO-TRAN-2495", "po_amt": "24.95"},
        {"vendor": "Coolblue B.V.", "po": "12572103", "po_amt": "670.99"},
        {"vendor": "Coolblue B.V.", "po": "12508334", "po_amt": "4584.06"},
        {"vendor": "SAECO", "po": "SCONL000000444", "po_amt": "49.99"},
    ]
    approved_no_po = ["Amazon Web Services, Inc.", "Free SAS", "Carter Inc"]
    unknown_vendors = [
        "OYO / Oravel Stays Private Limited",
        "Daniel Group",
        "Spencer Group",
        "West Group",
        "Stark Logistics GmbH",
        "Pinnacle Supplies Ltd",
        "Redwood Digital Inc",
        "Marquez & Associates",
        "Northwind Trading Co",
        "Apex Global Services",
    ]

    samples: list[dict[str, object]] = []
    seq = 0

    def _inv_num(prefix: str, n: int) -> str:
        return f"{prefix}-{n:04d}"

    def _amount_tag(amt: float) -> str:
        if amt < 100:
            return "under-100"
        if amt > 1000:
            return "over-1000"
        return "over-100"

    # ── Category 1: Clean auto-clear (approved vendor, exact PO, HIGH) ── ~25
    for i, vpo in enumerate(approved_with_po):
        po_amt = float(vpo["po_amt"])
        # Exact match
        samples.append({
            "label": f"Clean · {vpo['vendor']}",
            "expected": "AUTO_CLEAR — approved vendor, PO match, HIGH confidence",
            "tags": ["auto-clear", _amount_tag(po_amt)],
            "vendor": vpo["vendor"],
            "amount": vpo["po_amt"],
            "invoice_number": _inv_num("CLN", seq),
            "po_number": vpo["po"],
            "confidence": "HIGH",
            "source_file": None,
        })
        seq += 1
        # Second invoice, slightly different amount but within 5% tolerance
        within = round(po_amt * 1.03, 2)
        samples.append({
            "label": f"Within tolerance · {vpo['vendor']}",
            "expected": "AUTO_CLEAR — amount 3% over PO, within 5% tolerance",
            "tags": ["auto-clear", _amount_tag(within)],
            "vendor": vpo["vendor"],
            "amount": str(within),
            "invoice_number": _inv_num("TOL", seq),
            "po_number": vpo["po"],
            "confidence": "HIGH",
            "source_file": None,
        })
        seq += 1

    # Add some with varied small amounts
    small_amounts = [12.50, 27.99, 45.00, 67.80, 89.95]
    for i, amt in enumerate(small_amounts):
        vpo = approved_with_po[i % len(approved_with_po)]
        samples.append({
            "label": f"Small · {vpo['vendor']}",
            "expected": "AUTO_CLEAR — small amount, approved vendor",
            "tags": ["auto-clear", "under-100"],
            "vendor": vpo["vendor"],
            "amount": str(amt),
            "invoice_number": _inv_num("SML", seq),
            "po_number": vpo["po"],
            "confidence": "HIGH",
            "source_file": None,
        })
        seq += 1

    # ── Category 2: Over-PO escalation (amount > PO + tolerance) ── ~15
    over_pcts = [0.06, 0.08, 0.10, 0.12, 0.15, 0.20, 0.25, 0.30, 0.07, 0.09,
                 0.11, 0.18, 0.22, 0.14, 0.35]
    for i, pct in enumerate(over_pcts):
        vpo = approved_with_po[i % len(approved_with_po)]
        po_amt = float(vpo["po_amt"])
        over_amt = round(po_amt * (1 + pct), 2)
        pct_label = f"{int(pct * 100)}%"
        samples.append({
            "label": f"Over PO {pct_label} · {vpo['vendor']}",
            "expected": f"ESCALATE — amount {pct_label} over PO, exceeds 5% tolerance",
            "tags": ["escalate", "over-po", _amount_tag(over_amt)],
            "vendor": vpo["vendor"],
            "amount": str(over_amt),
            "invoice_number": _inv_num("OVR", seq),
            "po_number": vpo["po"],
            "confidence": "HIGH",
            "source_file": None,
        })
        seq += 1

    # ── Category 3: High amount, needs sign-off (above auto-approve limit) ── ~10
    high_amounts = [150.00, 250.00, 500.00, 1200.00, 2500.00,
                    3750.00, 5000.00, 7500.00, 10000.00, 15000.00]
    for i, amt in enumerate(high_amounts):
        vpo = approved_with_po[i % len(approved_with_po)]
        samples.append({
            "label": f"High amount ${amt:,.0f} · {vpo['vendor']}",
            "expected": "ESCALATE — clean but above auto-approve limit, needs sign-off",
            "tags": ["escalate", "high-amount", _amount_tag(amt)],
            "vendor": vpo["vendor"],
            "amount": str(amt),
            "invoice_number": _inv_num("HI", seq),
            "po_number": vpo["po"],
            "confidence": "HIGH",
            "source_file": None,
        })
        seq += 1

    # ── Category 4: No PO referenced (approved vendor) ── ~10
    no_po_amounts = [42.50, 88.00, 155.00, 299.99, 510.00,
                     725.00, 1100.00, 1850.00, 3200.00, 4999.00]
    for i, amt in enumerate(no_po_amounts):
        v = approved_no_po[i % len(approved_no_po)]
        samples.append({
            "label": f"No PO · {v}",
            "expected": "ESCALATE — approved vendor but no purchase order referenced",
            "tags": ["escalate", "no-po", _amount_tag(amt)],
            "vendor": v,
            "amount": str(amt),
            "invoice_number": _inv_num("NPO", seq),
            "po_number": None,
            "confidence": "HIGH",
            "source_file": None,
        })
        seq += 1

    # ── Category 5: Unknown vendor ── ~15
    unk_amounts = [35.00, 78.50, 120.00, 245.00, 499.99,
                   650.00, 890.00, 1350.00, 1999.00, 2750.00,
                   3500.00, 4200.00, 5800.00, 7999.00, 12500.00]
    for i, amt in enumerate(unk_amounts):
        v = unknown_vendors[i % len(unknown_vendors)]
        has_po = i % 3 == 0  # 1/3 have a PO, 2/3 don't
        tags: list[str] = ["escalate", "unknown-vendor", _amount_tag(amt)]
        if not has_po:
            tags.append("no-po")
        samples.append({
            "label": f"Unknown vendor · {v}",
            "expected": "ESCALATE — vendor not on approved list"
            + (", no PO" if not has_po else ""),
            "tags": tags,
            "vendor": v,
            "amount": str(amt),
            "invoice_number": _inv_num("UNK", seq),
            "po_number": f"PO-EXT-{seq}" if has_po else None,
            "confidence": "MED" if i % 2 == 0 else "LOW",
            "source_file": None,
        })
        seq += 1

    # ── Category 6: Low confidence extraction ── ~10
    low_conf_amounts = [19.99, 55.00, 132.50, 267.00, 445.00,
                        678.00, 950.00, 1400.00, 2100.00, 3800.00]
    for i, amt in enumerate(low_conf_amounts):
        vpo = approved_with_po[i % len(approved_with_po)]
        samples.append({
            "label": f"Low confidence · {vpo['vendor']}",
            "expected": "ESCALATE — extraction confidence too low for auto-clear",
            "tags": ["escalate", "low-confidence", _amount_tag(amt)],
            "vendor": vpo["vendor"],
            "amount": str(amt),
            "invoice_number": _inv_num("LOW", seq),
            "po_number": vpo["po"],
            "confidence": "LOW",
            "source_file": None,
        })
        seq += 1

    # ── Category 7: Exact duplicates (blocked) ── ~5
    dup_invoices = [
        ("SAECO", "49.99", "VF1005193039SCONL0303006280999", "SCONL000000444"),
        ("Azure Interior", "279.84", "INV/2025/NEW/0001", "CUSTREF123"),
        ("NETPRESSE", "56.02", "365146-DUP", "365146"),
        ("QualityHosting AG", "34.73", "CON02858-DUP", "CON02858"),
        ("Klein and Sons", "3.29", "PO-KLEIN-3290-DUP", "PO-KLEIN-3290"),
    ]
    for d_vendor, d_amt, d_inv_num, d_po in dup_invoices:
        samples.append({
            "label": f"Duplicate · {d_vendor}",
            "expected": "BLOCK — exact duplicate of a previously cleared invoice",
            "tags": ["block", "duplicate", _amount_tag(float(d_amt))],
            "vendor": d_vendor,
            "amount": d_amt,
            "invoice_number": d_inv_num,
            "po_number": d_po,
            "confidence": "MED",
            "source_file": None,
        })
        seq += 1

    # ── Category 8: Mixed scenarios (realistic variety) ── ~10
    mixed: list[tuple[str, str, str | None, str, str]] = [
        ("Herrera PLC", "16.45", "PO-HERRERA-1645", "HIGH", "Clean tiny invoice"),
        ("Tran, Hurst and Rodgers", "750.00", "PO-TRAN-2495", "HIGH", "Way over PO"),
        ("Coolblue B.V.", "670.99", "12572103", "LOW", "Exact PO but low confidence"),
        ("Carter Inc", "2999.00", None, "HIGH", "Big invoice, no PO"),
        ("Apex Global Services", "0.99", None, "LOW", "Tiny unknown vendor"),
        ("Azure Interior", "279.84", "CUSTREF123", "MED", "Exact PO but medium confidence"),
        ("Free SAS", "15000.00", None, "HIGH", "Huge amount, no PO"),
        ("Spencer Group", "50.00", "PO-SPENCER-17883", "HIGH", "Unknown vendor with PO"),
        ("West Group", "99.99", "PO-WEST-19126", "MED", "Unknown vendor, under limit"),
        ("Daniel Group", "104.97", "PO-DANIEL-10497", "LOW", "Unknown vendor, low confidence"),
    ]
    for m_vendor, m_amt, m_po, m_conf, m_desc in mixed:
        m_tags: list[str] = [_amount_tag(float(m_amt))]
        if m_vendor in ("Apex Global Services", "Spencer Group", "West Group",
                         "Daniel Group", "Pinnacle Supplies Ltd"):
            m_tags.append("unknown-vendor")
        if m_po is None:
            m_tags.append("no-po")
        if m_conf == "LOW":
            m_tags.append("low-confidence")
        if float(m_amt) > 1000:
            m_tags.append("high-amount")
        m_tags.append("escalate")  # all mixed scenarios escalate
        samples.append({
            "label": f"Mixed · {m_desc}",
            "expected": f"ESCALATE — {m_desc.lower()}",
            "tags": m_tags,
            "vendor": m_vendor,
            "amount": m_amt,
            "invoice_number": _inv_num("MIX", seq),
            "po_number": m_po,
            "confidence": m_conf,
            "source_file": None,
        })
        seq += 1

    # Deduplicate invoice_numbers (add hash suffix to guarantee uniqueness)
    seen: set[str] = set()
    dedup_seq = 0
    for s in samples:
        inv = str(s["invoice_number"])
        if inv in seen:
            dedup_seq += 1
            h = hashlib.sha256(f"{inv}-{dedup_seq}".encode()).hexdigest()[:6]
            s["invoice_number"] = f"{inv}-{h}"
        seen.add(str(s["invoice_number"]))

    return samples


@router.get("", response_model=list[InvoiceOut])
def list_invoices(
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org),
) -> list[InvoiceOut]:
    """Return today's invoices — the live working queue.

    The Inbox sidebar and chat both scope to today, so the API does too.
    Historical invoices are available via GET /invoices/all.
    """
    return [InvoiceOut.model_validate(i) for i in invoice_repo.list_today(db, org_id=org_id)]


@router.get("/all", response_model=list[InvoiceOut])
def list_all_invoices(
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org),
    limit: int = 200,
    offset: int = 0,
) -> list[InvoiceOut]:
    """Return ALL invoices across all dates — used by the History page."""
    return [
        InvoiceOut.model_validate(i)
        for i in invoice_repo.list_all(db, org_id=org_id, limit=limit, offset=offset)
    ]


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


@router.get("/{invoice_id}/file-url")
def get_invoice_file_url(
    invoice_id: str,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org),
) -> dict[str, str]:
    """Return a URL to preview the invoice document.

    For S3 files: returns a pre-signed URL (15 min expiry).
    For local files: returns a token-authenticated URL.
    """
    from app.clients import s3

    inv = invoice_repo.get(db, invoice_id, org_id=org_id)
    if inv is None:
        raise NotFoundError(f"invoice {invoice_id} not found")

    source = inv.source_file
    if not source:
        raise NotFoundError(f"invoice {invoice_id} has no associated file")

    if source.startswith("s3://"):
        key = source[5:]
        return {"url": s3.presigned_url(key)}

    # Local file — fall back to the /file endpoint with token auth
    return {"url": f"/api/v1/invoices/{invoice_id}/file"}


@router.get("/{invoice_id}/file")
def get_invoice_file(
    invoice_id: str,
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org),
) -> Response:
    """Serve local files directly. S3 files should use /file-url instead."""
    inv = invoice_repo.get(db, invoice_id, org_id=org_id)
    if inv is None:
        raise NotFoundError(f"invoice {invoice_id} not found")

    source = inv.source_file
    if not source:
        raise NotFoundError(f"invoice {invoice_id} has no associated file")

    # S3 files should go through /file-url endpoint
    if source.startswith("s3://"):
        from app.clients import s3

        key = source[5:]
        from fastapi.responses import RedirectResponse

        return RedirectResponse(url=s3.presigned_url(key), status_code=302)

    # Local absolute path
    if os.path.isabs(source):
        file_path = Path(source)
    else:
        # Relative filename — seed sample_invoices directory
        file_path = _SAMPLE_INVOICES_DIR / source

    # Validate resolved path is within allowed directories to prevent traversal
    resolved = file_path.resolve()
    allowed_dirs = [_SAMPLE_INVOICES_DIR.resolve(), _UPLOADS_DIR.resolve()]
    if not any(resolved.is_relative_to(d) for d in allowed_dirs):
        raise NotFoundError(f"file for invoice {invoice_id} not found on disk")

    if not file_path.exists():
        raise NotFoundError(f"file for invoice {invoice_id} not found on disk")

    media_type, _ = mimetypes.guess_type(str(file_path))
    if media_type is None:
        media_type = "application/octet-stream"

    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=file_path.name,
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
