"""Unit tests for app.seed.

The seed defines a deliberately legible demo: the TODAY queue
(``_BASE_SEED_INVOICES``) tells a clear story when processed —
5 auto-cleared, 6 escalated (3 unknown vendor, 1 missing PO, 1 over-tolerance,
1 over the auto-approve limit), and 1 blocked (exact duplicate). The corpus is
used only for HISTORY volume. These tests pin that story down.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db.models.invoice import Invoice
from app.db.models.organization import Organization
from app.db.models.purchase_order import PurchaseOrder
from app.db.models.vendor import Vendor
from app.domain.decision.thresholds import Verdict
from app.repositories import invoice_repo, vendor_repo
from app.seed import (
    DEMO_ORG_ID,
    _BASE_SEED_INVOICES,
    _CORPUS_TODAY_COUNT,
    is_empty,
    seed,
)
from app.services.pipeline_service import process_invoice

# The curated TODAY queue is the whole received batch (corpus is history-only).
_TODAY_COUNT = len(_BASE_SEED_INVOICES)            # 12
_EXPECTED_RECEIVED = _TODAY_COUNT + _CORPUS_TODAY_COUNT  # 12 + 0

# Expected verdict mix when the TODAY queue is processed.
_EXPECT_AUTO_CLEAR = 5
_EXPECT_ESCALATE = 6
_EXPECT_BLOCK = 1


def _inv_id(suffix: str, org_id: str = DEMO_ORG_ID) -> str:
    return f"inv-{suffix}-{org_id}"


def _ensure_demo_org(s: Session) -> None:
    if s.get(Organization, DEMO_ORG_ID) is None:
        s.add(Organization(id=DEMO_ORG_ID, name="Demo Co"))
        s.flush()


# ---------------------------------------------------------------------------
# Basic seed behaviour
# ---------------------------------------------------------------------------


def test_seed_returns_batch_count(db: Session) -> None:
    _ensure_demo_org(db)
    assert seed(db) == _EXPECTED_RECEIVED


def test_seed_inserts_vendors(db: Session) -> None:
    _ensure_demo_org(db)
    seed(db)
    names = {v.canonical_name for v in db.query(Vendor).all()}
    assert {"Azure Interior", "Coolblue B.V.", "SAECO", "Klein and Sons", "Carter Inc"} <= names


def test_unknown_vendors_are_unapproved(db: Session) -> None:
    """The unknown-vendor invoices' vendors are status 'new' (not approved), so
    they escalate regardless of amount."""
    _ensure_demo_org(db)
    seed(db)
    for name in ("Daniel Group", "Spencer Group", "West Group"):
        assert vendor_repo.status_of(db, name, org_id=DEMO_ORG_ID) == "new"


def test_seed_inserts_pos(db: Session) -> None:
    _ensure_demo_org(db)
    seed(db)
    po_numbers = {p.po_number for p in db.query(PurchaseOrder).all()}
    assert {"CUSTREF123", "12572103", "SCONL000000444", "PO-KLEIN-3290"} <= po_numbers


def test_seed_inserts_received_invoices(db: Session) -> None:
    _ensure_demo_org(db)
    seed(db)
    received = db.query(Invoice).filter(
        Invoice.status == "received", Invoice.org_id == DEMO_ORG_ID
    ).count()
    assert received == _EXPECTED_RECEIVED


def test_every_today_invoice_has_a_source_document(db: Session) -> None:
    _ensure_demo_org(db)
    seed(db)
    for d in _BASE_SEED_INVOICES:
        inv = db.query(Invoice).filter(Invoice.id == _inv_id(d["id_suffix"])).first()
        assert inv is not None, f"missing {d['id_suffix']}"
        assert inv.source_file and inv.source_file.endswith((".pdf", ".jpg"))


def test_seed_inserts_prior_cleared_invoices(db: Session) -> None:
    _ensure_demo_org(db)
    seed(db)
    saeco_prior = (
        db.query(Invoice)
        .filter(
            Invoice.status == "cleared",
            Invoice.vendor == "SAECO",
            Invoice.org_id == DEMO_ORG_ID,
        )
        .first()
    )
    assert saeco_prior is not None
    assert saeco_prior.invoice_number == "VF1005193039SCONL0303006280999"


def test_seed_idempotent_returns_zero_on_second_call(db: Session) -> None:
    _ensure_demo_org(db)
    assert seed(db) > 0
    assert seed(db) == 0


def test_seed_idempotent_no_duplicate_vendors(db: Session) -> None:
    _ensure_demo_org(db)
    seed(db)
    seed(db)
    names = [v.canonical_name for v in db.query(Vendor).filter(Vendor.org_id == DEMO_ORG_ID).all()]
    assert len(names) == len(set(names)), "Duplicate vendor names inserted"


def test_seed_force_reseeds(db: Session) -> None:
    _ensure_demo_org(db)
    n1 = seed(db)
    n2 = seed(db, force=True)
    assert n2 == n1
    received = db.query(Invoice).filter(
        Invoice.status == "received", Invoice.org_id == DEMO_ORG_ID
    ).count()
    assert received == n2


def test_is_empty_true_before_seed(db: Session) -> None:
    assert is_empty(db, org_id=DEMO_ORG_ID) is True


def test_is_empty_false_after_seed(db: Session) -> None:
    _ensure_demo_org(db)
    seed(db)
    assert is_empty(db, org_id=DEMO_ORG_ID) is False


# ---------------------------------------------------------------------------
# History (corpus) — backdated, varied statuses, .jpg documents
# ---------------------------------------------------------------------------


def test_history_invoices_exist_with_old_created_at(db: Session) -> None:
    _ensure_demo_org(db)
    seed(db)
    now = datetime.now(timezone.utc)
    history = (
        db.query(Invoice)
        .filter(
            Invoice.status != "received",
            Invoice.source_file.like("%.jpg"),
            Invoice.org_id == DEMO_ORG_ID,
        )
        .all()
    )
    assert len(history) > 0
    for inv in history:
        ts = inv.created_at
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        assert ts < now


def test_history_status_distribution(db: Session) -> None:
    _ensure_demo_org(db)
    seed(db)
    statuses = {
        inv.status
        for inv in db.query(Invoice).filter(
            Invoice.source_file.like("%.jpg"),
            Invoice.status != "received",
            Invoice.org_id == DEMO_ORG_ID,
        ).all()
    }
    assert {"cleared", "queued", "blocked", "needs", "routed"} <= statuses


# ---------------------------------------------------------------------------
# The TODAY story — per-scenario verdicts (this is the demo's whole point)
# ---------------------------------------------------------------------------


def _process(db: Session, suffix: str) -> Verdict:
    inv = invoice_repo.get(db, _inv_id(suffix))
    assert inv is not None, f"invoice {suffix} not found"
    inv_data = invoice_repo.to_domain(inv)
    result = process_invoice(db, inv_data, inv.confidence or "HIGH", org_id=DEMO_ORG_ID)
    return result.decision.verdict


def test_good_small_invoice_auto_clears(db: Session) -> None:
    """Klein & Sons — approved vendor, matched PO, HIGH conf, $3.29 (< $100) → AUTO_CLEAR."""
    _ensure_demo_org(db)
    seed(db)
    assert _process(db, "klein") is Verdict.AUTO_CLEAR


def test_unknown_vendor_escalates_despite_low_cost(db: Session) -> None:
    """Daniel Group — $104.97 with a matched PO, but vendor not approved → ESCALATE.

    Cost is not the only gate: an unknown vendor is never auto-approved.
    """
    _ensure_demo_org(db)
    seed(db)
    assert _process(db, "daniel") is Verdict.ESCALATE


def test_missing_po_escalates(db: Session) -> None:
    """Carter Inc — approved vendor but no PO → ESCALATE."""
    _ensure_demo_org(db)
    seed(db)
    assert _process(db, "carter") is Verdict.ESCALATE


def test_over_tolerance_escalates(db: Session) -> None:
    """Coolblue — ~7% over its PO → ESCALATE."""
    _ensure_demo_org(db)
    seed(db)
    assert _process(db, "coolblue-1") is Verdict.ESCALATE


def test_clean_but_over_limit_escalates_with_reason(db: Session) -> None:
    """Azure $279.84 — clean, but over the $100 auto-approve limit → ESCALATE."""
    _ensure_demo_org(db)
    seed(db)
    inv = invoice_repo.get(db, _inv_id("azure"))
    assert inv is not None
    result = process_invoice(db, invoice_repo.to_domain(inv), "HIGH", org_id=DEMO_ORG_ID)
    assert result.decision.verdict is Verdict.ESCALATE
    assert "limit" in result.decision.reason.lower()


def test_duplicate_blocks(db: Session) -> None:
    """SAECO — exact prior cleared invoice → BLOCK."""
    _ensure_demo_org(db)
    seed(db)
    assert _process(db, "saeco") is Verdict.BLOCK


def test_today_verdict_mix(db: Session) -> None:
    """The whole TODAY queue → 5 auto-clear, 6 escalate, 1 block."""
    _ensure_demo_org(db)
    seed(db)
    received = db.query(Invoice).filter(
        Invoice.status == "received", Invoice.org_id == DEMO_ORG_ID
    ).all()
    assert len(received) == _EXPECTED_RECEIVED

    verdicts: dict[str, int] = {"AUTO_CLEAR": 0, "ESCALATE": 0, "BLOCK": 0}
    for inv_row in received:
        inv_data = invoice_repo.to_domain(inv_row)
        result = process_invoice(db, inv_data, inv_row.confidence or "HIGH", org_id=DEMO_ORG_ID)
        verdicts[result.decision.verdict.value] += 1

    assert verdicts["AUTO_CLEAR"] == _EXPECT_AUTO_CLEAR, verdicts
    assert verdicts["ESCALATE"] == _EXPECT_ESCALATE, verdicts
    assert verdicts["BLOCK"] == _EXPECT_BLOCK, verdicts
