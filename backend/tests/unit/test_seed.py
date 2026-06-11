"""Unit tests for app.seed."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models.invoice import Invoice
from app.db.models.purchase_order import PurchaseOrder
from app.db.models.vendor import Vendor
from app.domain.decision.thresholds import Verdict
from app.repositories import invoice_repo
from app.seed import SEED_INVOICES, is_empty, seed
from app.services.pipeline_service import process_invoice


# ---------------------------------------------------------------------------
# Basic seed behaviour
# ---------------------------------------------------------------------------


def test_seed_returns_batch_count(db: Session) -> None:
    n = seed(db)
    assert n == len(SEED_INVOICES)
    assert n > 0


def test_seed_inserts_vendors(db: Session) -> None:
    seed(db)
    vendors = db.query(Vendor).all()
    canonical_names = {v.canonical_name for v in vendors}
    assert "Acme Corp" in canonical_names
    assert "Cyberdyne Systems" in canonical_names
    assert "Stark Industries" in canonical_names


def test_seed_inserts_pos(db: Session) -> None:
    seed(db)
    pos = db.query(PurchaseOrder).all()
    assert len(pos) > 0
    po_numbers = {p.po_number for p in pos}
    assert "PO-22841" in po_numbers   # Northwind escalation
    assert "PO-22760" in po_numbers   # Stark duplicate


def test_seed_inserts_received_invoices(db: Session) -> None:
    seed(db)
    received = db.query(Invoice).filter(Invoice.status == "received").all()
    assert len(received) == len(SEED_INVOICES)


def test_seed_inserts_prior_cleared_invoices(db: Session) -> None:
    seed(db)
    cleared = db.query(Invoice).filter(Invoice.status == "cleared").all()
    # Must have at least the Stark prior + cold-start rows
    assert len(cleared) > 0
    # The Stark prior must be present for duplicate detection
    stark_prior = (
        db.query(Invoice)
        .filter(Invoice.status == "cleared", Invoice.vendor == "Stark Industries")
        .first()
    )
    assert stark_prior is not None
    assert stark_prior.invoice_number == "INV-4502"


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
# Cyberdyne status is "new" (unapproved)
# ---------------------------------------------------------------------------


def test_cyberdyne_vendor_is_new(db: Session) -> None:
    seed(db)
    cyberdyne = db.query(Vendor).filter(Vendor.canonical_name == "Cyberdyne Systems").first()
    assert cyberdyne is not None
    assert cyberdyne.status == "new"


# ---------------------------------------------------------------------------
# Sanity: pipeline produces the expected verdicts after seed
# ---------------------------------------------------------------------------


def test_pipeline_routine_invoice_auto_clears(db: Session) -> None:
    """A routine invoice (in-tolerance, small, approved vendor) → AUTO_CLEAR."""
    seed(db)
    inv = invoice_repo.get(db, "INV-4472")
    assert inv is not None
    inv_data = invoice_repo.to_domain(inv)
    result = process_invoice(db, inv_data, "HIGH")
    assert result.decision.verdict is Verdict.AUTO_CLEAR


def test_pipeline_stark_duplicate_blocks(db: Session) -> None:
    """Stark INV-4502 has an exact prior cleared invoice → BLOCK."""
    seed(db)
    inv = invoice_repo.get(db, "INV-4502")
    assert inv is not None
    inv_data = invoice_repo.to_domain(inv)
    result = process_invoice(db, inv_data, "HIGH")
    assert result.decision.verdict is Verdict.BLOCK


def test_pipeline_cyberdyne_escalates(db: Session) -> None:
    """Cyberdyne INV-4495 has unknown vendor and no PO → ESCALATE."""
    seed(db)
    inv = invoice_repo.get(db, "INV-4495")
    assert inv is not None
    inv_data = invoice_repo.to_domain(inv)
    result = process_invoice(db, inv_data, "MED")
    assert result.decision.verdict is Verdict.ESCALATE


def test_pipeline_northwind_over_tolerance_escalates(db: Session) -> None:
    """Northwind INV-4471 is 13% over PO → ESCALATE."""
    seed(db)
    inv = invoice_repo.get(db, "INV-4471")
    assert inv is not None
    inv_data = invoice_repo.to_domain(inv)
    result = process_invoice(db, inv_data, "HIGH")
    assert result.decision.verdict is Verdict.ESCALATE


def test_pipeline_acme_over_tolerance_escalates(db: Session) -> None:
    """Acme INV-4483 is 6% over PO → ESCALATE."""
    seed(db)
    inv = invoice_repo.get(db, "INV-4483")
    assert inv is not None
    inv_data = invoice_repo.to_domain(inv)
    result = process_invoice(db, inv_data, "HIGH")
    assert result.decision.verdict is Verdict.ESCALATE
