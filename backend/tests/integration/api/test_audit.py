from __future__ import annotations

from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Payloads
# ---------------------------------------------------------------------------

CLEAR_PAYLOAD = {
    "vendor": "Acme Corp",
    "amount": "9800",
    "po_number": "PO-1",
    "invoice_number": "AUD-1",
    "confidence": "HIGH",
}


# ---------------------------------------------------------------------------
# GET /audit/{invoice_id} — non-empty events + chain verified
# ---------------------------------------------------------------------------


def test_audit_trail_after_invoice(seeded_client: TestClient) -> None:
    post_resp = seeded_client.post("/api/v1/invoices", json=CLEAR_PAYLOAD)
    assert post_resp.status_code == 201
    invoice_id = post_resp.json()["invoice_id"]

    resp = seeded_client.get(f"/api/v1/audit/{invoice_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data["events"], list)
    assert len(data["events"]) > 0
    assert data["chain_verified"] is True


# ---------------------------------------------------------------------------
# GET /audit — global log, newest first, chain verified
# ---------------------------------------------------------------------------


def test_global_audit_log_after_invoice(seeded_client: TestClient) -> None:
    post_resp = seeded_client.post("/api/v1/invoices", json=CLEAR_PAYLOAD)
    assert post_resp.status_code == 201

    resp = seeded_client.get("/api/v1/audit")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data["events"], list)
    assert len(data["events"]) > 0
    assert data["chain_verified"] is True
    # Verify newest-first ordering (seq should be descending)
    seqs = [e["seq"] for e in data["events"]]
    assert seqs == sorted(seqs, reverse=True)
