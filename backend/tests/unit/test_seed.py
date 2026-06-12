"""Unit tests for app.seed — based on the REAL invoice PDF seed dataset
plus the 100-image corpus expansion."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db.models.invoice import Invoice
from app.db.models.purchase_order import PurchaseOrder
from app.db.models.vendor import Vendor
from app.domain.decision.thresholds import Verdict
from app.repositories import invoice_repo
from app.seed import SEED_INVOICES, _CORPUS_TODAY_COUNT, is_empty, seed
from app.services.pipeline_service import process_invoice

# Expected counts — derived from seed logic:
#   10 PDF invoices + 12 corpus-today = 22 received
_PDF_COUNT = len(SEED_INVOICES)           # 10
_CORPUS_TODAY = _CORPUS_TODAY_COUNT       # 12
_EXPECTED_RECEIVED = _PDF_COUNT + _CORPUS_TODAY  # 22


# ---------------------------------------------------------------------------
# Basic seed behaviour
# ---------------------------------------------------------------------------


def test_seed_returns_batch_count(db: Session) -> None:
    n = seed(db)
    assert n == _EXPECTED_RECEIVED


def test_seed_inserts_vendors(db: Session) -> None:
    seed(db)
    vendors = db.query(Vendor).all()
    canonical_names = {v.canonical_name for v in vendors}
    assert "Azure Interior" in canonical_names
    assert "Coolblue B.V." in canonical_names
    assert "SAECO" in canonical_names
    assert "OYO / Oravel Stays Private Limited" in canonical_names


def test_seed_inserts_pos(db: Session) -> None:
    seed(db)
    pos = db.query(PurchaseOrder).all()
    assert len(pos) > 0
    po_numbers = {p.po_number for p in pos}
    assert "CUSTREF123" in po_numbers          # Azure Interior auto-clear
    assert "12572103" in po_numbers            # Coolblue over-PO
    assert "SCONL000000444" in po_numbers      # SAECO duplicate


def test_seed_inserts_received_invoices(db: Session) -> None:
    seed(db)
    received = db.query(Invoice).filter(Invoice.status == "received").all()
    assert len(received) == _EXPECTED_RECEIVED


def test_seed_inserts_prior_cleared_invoices(db: Session) -> None:
    seed(db)
    cleared = db.query(Invoice).filter(Invoice.status == "cleared").all()
    # Must have at least the SAECO prior + cold-start rows
    assert len(cleared) > 0
    # The SAECO prior must be present for duplicate detection
    saeco_prior = (
        db.query(Invoice)
        .filter(Invoice.status == "cleared", Invoice.vendor == "SAECO")
        .first()
    )
    assert saeco_prior is not None
    assert saeco_prior.invoice_number == "VF1005193039SCONL0303006280999"


def test_seed_idempotent_returns_zero_on_second_call(db: Session) -> None:
    n1 = seed(db)
    assert n1 > 0
    n2 = seed(db)
    assert n2 == 0


def test_seed_idempotent_no_duplicate_vendors(db: Session) -> None:
    seed(db)
    seed(db)
    vendors = db.query(Vendor).all()
    names = [v.canonical_name for v in vendors]
    assert len(names) == len(set(names)), "Duplicate vendor names inserted"


def test_seed_force_reseeds(db: Session) -> None:
    n1 = seed(db)
    assert n1 > 0
    n2 = seed(db, force=True)
    assert n2 == n1
    # Only one batch of received invoices after force-reseed
    received = db.query(Invoice).filter(Invoice.status == "received").count()
    assert received == n2


def test_is_empty_true_before_seed(db: Session) -> None:
    assert is_empty(db) is True


def test_is_empty_false_after_seed(db: Session) -> None:
    seed(db)
    assert is_empty(db) is False


def test_is_empty_true_after_force_wipe_then_seed(db: Session) -> None:
    seed(db)
    # Manually wipe received invoices to simulate empty state
    db.query(Invoice).filter(Invoice.status == "received").delete()
    db.flush()
    assert is_empty(db) is True


# ---------------------------------------------------------------------------
# OYO vendor is "new" (unapproved)
# ---------------------------------------------------------------------------


def test_oyo_vendor_is_new(db: Session) -> None:
    seed(db)
    oyo = db.query(Vendor).filter(Vendor.canonical_name == "OYO / Oravel Stays Private Limited").first()
    assert oyo is not None
    assert oyo.status == "new"


# ---------------------------------------------------------------------------
# source_file is set on PDF seed invoices (all .pdf)
# ---------------------------------------------------------------------------


def test_seed_pdf_invoices_have_source_file(db: Session) -> None:
    seed(db)
    for inv_id in [i.id for i in SEED_INVOICES]:
        inv = db.query(Invoice).filter(Invoice.id == inv_id).first()
        assert inv is not None
        assert inv.source_file is not None, f"Invoice {inv.id} missing source_file"
        assert inv.source_file.endswith(".pdf"), f"Invoice {inv.id} source_file not PDF: {inv.source_file}"


# ---------------------------------------------------------------------------
# Corpus today batch — received, .jpg source_file
# ---------------------------------------------------------------------------


def test_corpus_today_invoices_are_received(db: Session) -> None:
    seed(db)
    corpus_today = (
        db.query(Invoice)
        .filter(Invoice.status == "received", Invoice.source_file.like("%.jpg"))
        .all()
    )
    assert len(corpus_today) == _CORPUS_TODAY


def test_corpus_today_invoices_have_jpg_source_file(db: Session) -> None:
    seed(db)
    corpus_today = (
        db.query(Invoice)
        .filter(Invoice.status == "received", Invoice.source_file.like("%.jpg"))
        .all()
    )
    for inv in corpus_today:
        assert inv.source_file is not None
        assert inv.source_file.endswith(".jpg"), f"{inv.id} source_file={inv.source_file}"


# ---------------------------------------------------------------------------
# History invoices — backdated created_at + non-null source_file
# ---------------------------------------------------------------------------


def test_history_invoices_exist_with_old_created_at(db: Session) -> None:
    seed(db)
    now = datetime.now(timezone.utc)
    history = (
        db.query(Invoice)
        .filter(
            Invoice.status != "received",
            Invoice.source_file.like("%.jpg"),
        )
        .all()
    )
    assert len(history) > 0, "Expected history corpus invoices with .jpg source_file"
    # Every history corpus invoice must have created_at strictly before now
    for inv in history:
        ts = inv.created_at
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        assert ts < now, f"{inv.id} created_at={ts} is not in the past"


def test_history_status_distribution(db: Session) -> None:
    """Verify the pre-set history statuses contain all expected categories."""
    seed(db)
    history = (
        db.query(Invoice)
        .filter(
            Invoice.source_file.like("%.jpg"),
            Invoice.status != "received",
        )
        .all()
    )
    statuses = {inv.status for inv in history}
    # Expect all five history status values to appear
    assert "cleared" in statuses
    assert "queued" in statuses
    assert "blocked" in statuses
    assert "needs" in statuses
    assert "routed" in statuses


# ---------------------------------------------------------------------------
# Sanity: pipeline produces the expected verdicts after seed (PDF batch only)
# ---------------------------------------------------------------------------


def test_pipeline_azure_auto_clears(db: Session) -> None:
    """Azure Interior — approved vendor, PO match, HIGH confidence, within tolerance → AUTO_CLEAR."""
    seed(db)
    inv = invoice_repo.get(db, "inv-azure")
    assert inv is not None
    inv_data = invoice_repo.to_domain(inv)
    result = process_invoice(db, inv_data, "HIGH")
    assert result.decision.verdict is Verdict.AUTO_CLEAR


def test_pipeline_saeco_duplicate_blocks(db: Session) -> None:
    """SAECO inv-saeco has an exact prior cleared invoice → BLOCK."""
    seed(db)
    inv = invoice_repo.get(db, "inv-saeco")
    assert inv is not None
    inv_data = invoice_repo.to_domain(inv)
    result = process_invoice(db, inv_data, "MED")
    assert result.decision.verdict is Verdict.BLOCK


def test_pipeline_oyo_escalates(db: Session) -> None:
    """OYO has unknown vendor and no PO → ESCALATE."""
    seed(db)
    inv = invoice_repo.get(db, "inv-oyo")
    assert inv is not None
    inv_data = invoice_repo.to_domain(inv)
    result = process_invoice(db, inv_data, "LOW")
    assert result.decision.verdict is Verdict.ESCALATE


def test_pipeline_coolblue1_over_tolerance_escalates(db: Session) -> None:
    """Coolblue-1 is ~7% over PO → ESCALATE."""
    seed(db)
    inv = invoice_repo.get(db, "inv-coolblue-1")
    assert inv is not None
    inv_data = invoice_repo.to_domain(inv)
    result = process_invoice(db, inv_data, "HIGH")
    assert result.decision.verdict is Verdict.ESCALATE


def test_pipeline_aws_low_confidence_escalates(db: Session) -> None:
    """Amazon Web Services has LOW confidence and no PO → ESCALATE."""
    seed(db)
    inv = invoice_repo.get(db, "inv-aws")
    assert inv is not None
    inv_data = invoice_repo.to_domain(inv)
    result = process_invoice(db, inv_data, "LOW")
    assert result.decision.verdict is Verdict.ESCALATE


# ---------------------------------------------------------------------------
# Verdict mix — PDF batch produces 4 AUTO_CLEAR / 5 ESCALATE / 1 BLOCK
# Corpus today invoices (no PO, approved vendor) → ESCALATE (MISSING_PO / LOW)
# ---------------------------------------------------------------------------


def test_seed_pdf_verdict_mix(db: Session) -> None:
    """Seed + process the 10 PDF received invoices → expected verdict mix."""
    seed(db)

    pdf_received = (
        db.query(Invoice)
        .filter(Invoice.status == "received", Invoice.source_file.like("%.pdf"))
        .all()
    )
    assert len(pdf_received) == _PDF_COUNT  # 10

    verdicts: dict[str, int] = {"AUTO_CLEAR": 0, "ESCALATE": 0, "BLOCK": 0}
    for inv_row in pdf_received:
        inv_data = invoice_repo.to_domain(inv_row)
        confidence = inv_row.confidence or "HIGH"
        result = process_invoice(db, inv_data, confidence)
        verdicts[result.decision.verdict.value] += 1

    assert verdicts["AUTO_CLEAR"] == 4, f"Expected 4 AUTO_CLEAR, got {verdicts}"
    assert verdicts["ESCALATE"] == 5, f"Expected 5 ESCALATE, got {verdicts}"
    assert verdicts["BLOCK"] == 1, f"Expected 1 BLOCK, got {verdicts}"


def test_seed_corpus_today_all_escalate(db: Session) -> None:
    """Corpus today invoices have no PO → all ESCALATE."""
    seed(db)

    corpus_today = (
        db.query(Invoice)
        .filter(Invoice.status == "received", Invoice.source_file.like("%.jpg"))
        .all()
    )
    assert len(corpus_today) == _CORPUS_TODAY

    for inv_row in corpus_today:
        inv_data = invoice_repo.to_domain(inv_row)
        confidence = inv_row.confidence or "LOW"
        result = process_invoice(db, inv_data, confidence)
        assert result.decision.verdict is Verdict.ESCALATE, (
            f"{inv_row.id} expected ESCALATE, got {result.decision.verdict}"
        )


def test_full_received_verdict_mix(db: Session) -> None:
    """All 22 received invoices: exactly 4 AUTO_CLEAR, 1 BLOCK, rest ESCALATE."""
    seed(db)

    received = db.query(Invoice).filter(Invoice.status == "received").all()
    assert len(received) == _EXPECTED_RECEIVED  # 22

    verdicts: dict[str, int] = {"AUTO_CLEAR": 0, "ESCALATE": 0, "BLOCK": 0}
    for inv_row in received:
        inv_data = invoice_repo.to_domain(inv_row)
        confidence = inv_row.confidence or "LOW"
        result = process_invoice(db, inv_data, confidence)
        verdicts[result.decision.verdict.value] += 1

    assert verdicts["AUTO_CLEAR"] == 4, f"Expected 4 AUTO_CLEAR, got {verdicts}"
    assert verdicts["BLOCK"] == 1, f"Expected 1 BLOCK, got {verdicts}"
    # All the rest are ESCALATE
    assert verdicts["ESCALATE"] == _EXPECTED_RECEIVED - 4 - 1, (
        f"Expected {_EXPECTED_RECEIVED - 5} ESCALATE, got {verdicts}"
    )
