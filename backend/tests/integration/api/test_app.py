from __future__ import annotations

from fastapi.testclient import TestClient

# (Static frontend serving is production-only — the built Vite app is copied in
# and served by the API in the Docker image; in dev the frontend runs on Vite.)

# ---------------------------------------------------------------------------
# E2E smoke — full multi-router round-trip
# ---------------------------------------------------------------------------

CLEAR_PAYLOAD = {
    "vendor": "Acme Corp",
    "amount": "9800",
    "po_number": "PO-1",
    "invoice_number": "E2E-1",
    "confidence": "HIGH",
}


def test_e2e_invoice_approve_audit(seeded_client: TestClient) -> None:
    # 1. POST invoice — auto-clear
    post_resp = seeded_client.post("/api/v1/invoices", json=CLEAR_PAYLOAD)
    assert post_resp.status_code == 201
    invoice_id = post_resp.json()["invoice_id"]

    # 2. GET invoice by id
    get_resp = seeded_client.get(f"/api/v1/invoices/{invoice_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == invoice_id

    # 3. POST action — approve
    action_resp = seeded_client.post(
        f"/api/v1/invoices/{invoice_id}/action",
        json={"action": "approve"},
    )
    assert action_resp.status_code == 200

    # 4. GET audit trail — non-empty and chain verified
    audit_resp = seeded_client.get(f"/api/v1/audit/{invoice_id}")
    assert audit_resp.status_code == 200
    data = audit_resp.json()
    assert isinstance(data["events"], list)
    assert len(data["events"]) > 0
    assert data["chain_verified"] is True
