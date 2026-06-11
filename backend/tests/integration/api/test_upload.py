"""Integration tests for POST /api/v1/invoices/upload."""
from __future__ import annotations

from fastapi.testclient import TestClient


PLAIN_FILE_FULL = (
    "inv.txt",
    b"vendor: Acme Corp\namount: 9800\npo: PO-1\ninvoice_number: A-1",
    "text/plain",
)

# The format requested in the spec: Vendor / Invoice # / Amount / PO
PLAIN_FILE_SPEC_FORMAT = (
    "spec_invoice.txt",
    b"Vendor: Acme Corp\nInvoice: INV-9100\nAmount: 1500\nPO: PO-22845",
    "text/plain",
)

PLAIN_FILE_NO_AMOUNT = (
    "inv_low.txt",
    b"vendor: Acme Corp\npo: PO-1\ninvoice_number: B-1",
    "text/plain",
)


# ---------------------------------------------------------------------------
# HIGH-confidence upload → 201 with a verdict
# ---------------------------------------------------------------------------


def test_upload_full_invoice_returns_201(seeded_client: TestClient) -> None:
    resp = seeded_client.post(
        "/api/v1/invoices/upload",
        files={"file": PLAIN_FILE_FULL},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "verdict" in data
    assert data["verdict"] in ("AUTO_CLEAR", "ESCALATE", "BLOCK")


def test_upload_full_invoice_has_invoice_id(seeded_client: TestClient) -> None:
    resp = seeded_client.post(
        "/api/v1/invoices/upload",
        files={"file": PLAIN_FILE_FULL},
    )
    assert resp.status_code == 201
    assert resp.json()["invoice_id"].startswith("inv-")


# ---------------------------------------------------------------------------
# Missing amount → overall LOW → verdict ESCALATE
# ---------------------------------------------------------------------------


def test_upload_missing_amount_escalates(seeded_client: TestClient) -> None:
    resp = seeded_client.post(
        "/api/v1/invoices/upload",
        files={"file": PLAIN_FILE_NO_AMOUNT},
    )
    assert resp.status_code == 201
    data = resp.json()
    # LOW confidence → guard must escalate (cannot AUTO_CLEAR with uncertain data)
    assert data["verdict"] == "ESCALATE"


# ---------------------------------------------------------------------------
# Spec-format upload (Vendor / Invoice / Amount / PO) → 201 + created invoice
# ---------------------------------------------------------------------------


def test_upload_spec_format_returns_201(seeded_client: TestClient) -> None:
    """POST a tiny in-memory text/plain file in the Vendor/Invoice/Amount/PO
    format and assert 201 + a created invoice_id."""
    resp = seeded_client.post(
        "/api/v1/invoices/upload",
        files={"file": PLAIN_FILE_SPEC_FORMAT},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "invoice_id" in data
    assert data["invoice_id"].startswith("inv-")


# ---------------------------------------------------------------------------
# GET /invoices/samples — returns InvoiceIn-shaped samples
# ---------------------------------------------------------------------------


def test_get_samples_returns_four_items(seeded_client: TestClient) -> None:
    resp = seeded_client.get("/api/v1/invoices/samples")
    assert resp.status_code == 200
    samples = resp.json()
    assert len(samples) == 4


def test_get_samples_have_required_fields(seeded_client: TestClient) -> None:
    resp = seeded_client.get("/api/v1/invoices/samples")
    assert resp.status_code == 200
    for sample in resp.json():
        assert "vendor" in sample
        assert "amount" in sample
        assert "invoice_number" in sample
        assert "label" in sample
        assert "expected" in sample


def test_get_samples_invoice_numbers_fresh(seeded_client: TestClient) -> None:
    """Sample invoice numbers should be in the INV-9001..9004 range."""
    resp = seeded_client.get("/api/v1/invoices/samples")
    non_duplicate_samples = [
        s for s in resp.json()
        if s["label"] != "Exact duplicate"  # duplicate intentionally reuses INV-4502
    ]
    for sample in non_duplicate_samples:
        assert sample["invoice_number"].startswith("INV-9")
