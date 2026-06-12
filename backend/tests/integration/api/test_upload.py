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
        # Every sample must now include a source_file for PDF preview
        assert "source_file" in sample
        assert sample["source_file"] is not None
        assert sample["source_file"].endswith(".pdf")


def test_get_samples_invoice_numbers_are_new(seeded_client: TestClient) -> None:
    """Non-duplicate samples use new invoice numbers distinct from the seed batch."""
    resp = seeded_client.get("/api/v1/invoices/samples")
    non_duplicate_samples = [
        s for s in resp.json()
        if s["label"] != "Exact duplicate"  # duplicate intentionally reuses a real invoice_number
    ]
    # Each should have a unique, non-empty invoice_number
    invoice_numbers = [s["invoice_number"] for s in non_duplicate_samples]
    assert len(invoice_numbers) == len(set(invoice_numbers)), "Duplicate invoice numbers in samples"
    for inv_num in invoice_numbers:
        assert inv_num, "Invoice number must not be empty"


def test_get_samples_known_invoice_numbers(seeded_client: TestClient) -> None:
    """Verify the specific invoice numbers specified in the samples."""
    resp = seeded_client.get("/api/v1/invoices/samples")
    samples = {s["label"]: s for s in resp.json()}
    assert samples["Clean auto-clear"]["invoice_number"] == "INV/2025/NEW/0001"
    assert samples["Over-PO escalation"]["invoice_number"] == "CB-NEW-0001"
    assert samples["Unknown vendor / no PO"]["invoice_number"] == "IBZY-NEW-01"
    assert samples["Exact duplicate"]["invoice_number"] == "VF1005193039SCONL0303006280999"


def test_get_samples_source_files(seeded_client: TestClient) -> None:
    """Verify sample source_file mappings."""
    resp = seeded_client.get("/api/v1/invoices/samples")
    samples = {s["label"]: s for s in resp.json()}
    assert samples["Clean auto-clear"]["source_file"] == "AzureInterior.pdf"
    assert samples["Over-PO escalation"]["source_file"] == "coolblue1.pdf"
    assert samples["Unknown vendor / no PO"]["source_file"] == "oyo.pdf"
    assert samples["Exact duplicate"]["source_file"] == "saeco.pdf"


def test_post_sample_with_source_file_serves_pdf(demo_seeded_client: TestClient) -> None:
    """POST a sample invoice with source_file → GET /file returns 200 application/pdf."""
    # Use the "Clean auto-clear" sample payload
    payload = {
        "vendor": "Azure Interior",
        "amount": "279.84",
        "invoice_number": "INV/2025/NEW/0001",
        "po_number": "CUSTREF123",
        "confidence": "HIGH",
        "source_file": "AzureInterior.pdf",
    }
    post_resp = demo_seeded_client.post("/api/v1/invoices", json=payload)
    assert post_resp.status_code == 201
    invoice_id = post_resp.json()["invoice_id"]

    file_resp = demo_seeded_client.get(f"/api/v1/invoices/{invoice_id}/file")
    assert file_resp.status_code == 200
    assert file_resp.headers["content-type"].startswith("application/pdf")
    assert file_resp.content[:4] == b"%PDF"


def test_post_sample_source_file_in_invoice_out(demo_seeded_client: TestClient) -> None:
    """After POSTing with source_file, GET /invoices/{id} returns source_file."""
    payload = {
        "vendor": "OYO / Oravel Stays Private Limited",
        "amount": "1939",
        "invoice_number": "IBZY-NEW-01",
        "po_number": None,
        "confidence": "LOW",
        "source_file": "oyo.pdf",
    }
    post_resp = demo_seeded_client.post("/api/v1/invoices", json=payload)
    assert post_resp.status_code == 201
    invoice_id = post_resp.json()["invoice_id"]

    get_resp = demo_seeded_client.get(f"/api/v1/invoices/{invoice_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["source_file"] == "oyo.pdf"
