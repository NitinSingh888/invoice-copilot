from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.conftest import TEST_ORG_ID

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


def test_get_invoice_file_returns_200_pdf(demo_seeded_client: TestClient) -> None:
    """A seed invoice with a real PDF → GET /file returns 200 + application/pdf."""
    inv_id = f"inv-azure-{TEST_ORG_ID}"
    resp = demo_seeded_client.get(f"/api/v1/invoices/{inv_id}/file")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/pdf")


def test_get_invoice_file_returns_pdf_bytes(demo_seeded_client: TestClient) -> None:
    """File response body starts with the PDF magic bytes (%PDF)."""
    inv_id = f"inv-azure-{TEST_ORG_ID}"
    resp = demo_seeded_client.get(f"/api/v1/invoices/{inv_id}/file")
    assert resp.status_code == 200
    assert resp.content[:4] == b"%PDF"


def test_get_invoice_file_unknown_id_returns_404(demo_seeded_client: TestClient) -> None:
    """Unknown invoice id → 404."""
    resp = demo_seeded_client.get("/api/v1/invoices/inv-does-not-exist/file")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"]


def test_get_corpus_image_file_returns_200(demo_seeded_client: TestClient) -> None:
    """Corpus image invoice → GET /file returns 200."""
    inv_id = f"inv-c000-{TEST_ORG_ID}"
    resp = demo_seeded_client.get(f"/api/v1/invoices/{inv_id}/file")
    assert resp.status_code == 200


def test_corpus_today_invoices_are_from_today(demo_seeded_client: TestClient) -> None:
    """GET /invoices (list_today) returns only today's corpus invoices."""
    from datetime import date, datetime

    rows = demo_seeded_client.get("/api/v1/invoices").json()
    corpus = [r for r in rows if (r.get("source_file") or "").lower().endswith(".jpg")]
    today_rows = [r for r in corpus if r["status"] == "received"]
    assert today_rows, "Expected at least one today corpus invoice"

    for r in today_rows:
        created = datetime.fromisoformat(r["created_at"]).date()
        assert created == date.today(), f"Invoice {r['id']} created_at {created} is not today"


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
        org_id=TEST_ORG_ID,
    )
    db.add(inv)
    db.commit()

    resp = client.get("/api/v1/invoices/inv-no-file/file")
    assert resp.status_code == 404


def test_invoice_out_exposes_source_file(demo_seeded_client: TestClient) -> None:
    """GET /invoices/{id} includes source_file field in InvoiceOut."""
    inv_id = f"inv-azure-{TEST_ORG_ID}"
    resp = demo_seeded_client.get(f"/api/v1/invoices/{inv_id}")
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
        org_id=TEST_ORG_ID,
    )
    db.add(inv)
    db.commit()

    resp = client.get("/api/v1/invoices/inv-nf-2")
    assert resp.status_code == 200
    assert resp.json()["source_file"] is None


# ---------------------------------------------------------------------------
# InvoiceOut.created_at — ISO-8601 string
# ---------------------------------------------------------------------------


def test_invoice_out_exposes_created_at(client: TestClient, db: Session) -> None:
    """GET /invoices/{id} includes a non-empty ISO-8601 created_at string."""
    from app.db.models.invoice import Invoice as InvoiceModel
    from decimal import Decimal

    inv = InvoiceModel(
        id="inv-ts-1",
        invoice_number="TS-001",
        status="received",
        vendor="Timestamp Vendor",
        amount=Decimal("500.00"),
        confidence="HIGH",
        org_id=TEST_ORG_ID,
    )
    db.add(inv)
    db.commit()

    resp = client.get("/api/v1/invoices/inv-ts-1")
    assert resp.status_code == 200
    data = resp.json()
    assert "created_at" in data
    created_at = data["created_at"]
    assert isinstance(created_at, str)
    assert len(created_at) > 0
    # Validate it is parseable as ISO-8601
    from datetime import datetime
    parsed = datetime.fromisoformat(created_at)
    assert parsed is not None
