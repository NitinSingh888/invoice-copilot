"""Integration tests for POST /api/v1/invoices/upload."""
from __future__ import annotations

from fastapi.testclient import TestClient


PLAIN_FILE_FULL = (
    "inv.txt",
    b"vendor: Acme Corp\namount: 9800\npo: PO-1\ninvoice_number: A-1",
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
