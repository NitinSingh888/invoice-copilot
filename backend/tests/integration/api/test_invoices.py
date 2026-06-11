from __future__ import annotations

from fastapi.testclient import TestClient


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
