from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.seed import seed


# ---------------------------------------------------------------------------
# Payloads
# ---------------------------------------------------------------------------

CLEAR_PAYLOAD = {
    "vendor": "Acme Corp",
    "amount": "9800",
    "po_number": "PO-1",
    "invoice_number": "A-1",
    "confidence": "HIGH",
}

ESCALATE_PAYLOAD = {
    "vendor": "Acme Corp",
    "amount": "11300",
    "po_number": "PO-1",
    "invoice_number": "B-1",
    "confidence": "HIGH",
}


# ---------------------------------------------------------------------------
# POST /invoices — auto-clear
# ---------------------------------------------------------------------------


def test_post_invoice_auto_clear(seeded_client: TestClient) -> None:
    resp = seeded_client.post("/api/v1/invoices", json=CLEAR_PAYLOAD)
    assert resp.status_code == 201
    data = resp.json()
    assert data["verdict"] == "AUTO_CLEAR"
    assert data["status"] == "queued"
    assert "invoice_id" in data


# ---------------------------------------------------------------------------
# POST /invoices — escalate over tolerance
# ---------------------------------------------------------------------------


def test_post_invoice_escalate(seeded_client: TestClient) -> None:
    resp = seeded_client.post("/api/v1/invoices", json=ESCALATE_PAYLOAD)
    assert resp.status_code == 201
    data = resp.json()
    assert data["verdict"] == "ESCALATE"
    assert data["status"] == "needs"


# ---------------------------------------------------------------------------
# GET /invoices — list non-empty
# ---------------------------------------------------------------------------


def test_list_invoices_non_empty(seeded_client: TestClient) -> None:
    seeded_client.post("/api/v1/invoices", json=CLEAR_PAYLOAD)
    resp = seeded_client.get("/api/v1/invoices")
    assert resp.status_code == 200
    items = resp.json()
    assert isinstance(items, list)
    assert len(items) > 0


# ---------------------------------------------------------------------------
# GET /invoices/{id} — found and not found
# ---------------------------------------------------------------------------


def test_get_invoice_by_id(seeded_client: TestClient) -> None:
    post = seeded_client.post("/api/v1/invoices", json=CLEAR_PAYLOAD)
    invoice_id = post.json()["invoice_id"]
    resp = seeded_client.get(f"/api/v1/invoices/{invoice_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == invoice_id


def test_get_invoice_missing(seeded_client: TestClient) -> None:
    resp = seeded_client.get("/api/v1/invoices/does-not-exist-xyz")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# POST /{id}/action — route escalated invoice
# ---------------------------------------------------------------------------


def test_invoice_action_route(seeded_client: TestClient) -> None:
    # Create an escalated invoice first
    post = seeded_client.post("/api/v1/invoices", json=ESCALATE_PAYLOAD)
    assert post.status_code == 201
    invoice_id = post.json()["invoice_id"]
    assert post.json()["verdict"] == "ESCALATE"

    # Route it as priya
    resp = seeded_client.post(
        f"/api/v1/invoices/{invoice_id}/action",
        json={"action": "route"},
        headers={"X-Role": "priya"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "routed"


# ---------------------------------------------------------------------------
# GET /invoices/{id}/file — document preview endpoint
# ---------------------------------------------------------------------------


@pytest.fixture
def demo_seeded_client(client: TestClient, db: Session) -> TestClient:
    """Client with the full demo seed loaded (real invoice PDFs)."""
    seed(db)
    db.commit()
    return client


def test_get_invoice_file_returns_200_pdf(demo_seeded_client: TestClient) -> None:
    """A seed invoice with a real PDF → GET /file returns 200 + application/pdf."""
    resp = demo_seeded_client.get("/api/v1/invoices/inv-azure/file")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/pdf")


def test_get_invoice_file_returns_pdf_bytes(demo_seeded_client: TestClient) -> None:
    """File response body starts with the PDF magic bytes (%PDF)."""
    resp = demo_seeded_client.get("/api/v1/invoices/inv-azure/file")
    assert resp.status_code == 200
    assert resp.content[:4] == b"%PDF"


def test_get_invoice_file_unknown_id_returns_404(demo_seeded_client: TestClient) -> None:
    """Unknown invoice id → 404."""
    resp = demo_seeded_client.get("/api/v1/invoices/inv-does-not-exist/file")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"]


def test_get_invoice_file_no_file_returns_404(client: TestClient, db: Session) -> None:
    """Invoice with no source_file set → 404."""
    from app.db.models.invoice import Invoice as InvoiceModel
    from decimal import Decimal

    inv = InvoiceModel(
        id="inv-no-file",
        invoice_number="NF-001",
        status="received",
        vendor="Test Vendor",
        amount=Decimal("100.00"),
        confidence="HIGH",
        source_file=None,
    )
    db.add(inv)
    db.commit()

    resp = client.get("/api/v1/invoices/inv-no-file/file")
    assert resp.status_code == 404


def test_invoice_out_exposes_source_file(demo_seeded_client: TestClient) -> None:
    """GET /invoices/{id} includes source_file field in InvoiceOut."""
    resp = demo_seeded_client.get("/api/v1/invoices/inv-azure")
    assert resp.status_code == 200
    data = resp.json()
    assert "source_file" in data
    assert data["source_file"] == "AzureInterior.pdf"


def test_invoice_out_source_file_none_for_no_file(client: TestClient, db: Session) -> None:
    """Invoice with no source_file → source_file is null in InvoiceOut."""
    from app.db.models.invoice import Invoice as InvoiceModel
    from decimal import Decimal

    inv = InvoiceModel(
        id="inv-nf-2",
        invoice_number="NF-002",
        status="received",
        vendor="Test Vendor",
        amount=Decimal("100.00"),
        confidence="HIGH",
        source_file=None,
    )
    db.add(inv)
    db.commit()

    resp = client.get("/api/v1/invoices/inv-nf-2")
    assert resp.status_code == 200
    assert resp.json()["source_file"] is None
