"""Integration tests for new features: comments, reject action, soft-delete, FK guard."""
from __future__ import annotations

from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models.invoice import Invoice


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ESCALATE_PAYLOAD = {
    "vendor": "Acme Corp",
    "amount": "11300",
    "po_number": "PO-1",
    "invoice_number": "B-1",
    "confidence": "HIGH",
}


def _post_invoice(client: TestClient, payload: dict) -> str:  # type: ignore[type-arg]
    resp = client.post("/api/v1/invoices", json=payload)
    assert resp.status_code == 201
    return resp.json()["invoice_id"]


# ---------------------------------------------------------------------------
# Comments — add and list
# ---------------------------------------------------------------------------


def test_add_comment_returns_201(seeded_client: TestClient) -> None:
    inv_id = _post_invoice(seeded_client, ESCALATE_PAYLOAD)
    resp = seeded_client.post(
        f"/api/v1/invoices/{inv_id}/comments",
        json={"body": "This looks suspicious."},
        headers={"X-Role": "priya"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["invoice_id"] == inv_id
    assert data["body"] == "This looks suspicious."
    assert data["author"] == "priya"
    assert "id" in data
    assert data["id"].startswith("cmt-")
    assert "created_at" in data


def test_list_comments_returns_oldest_first(seeded_client: TestClient) -> None:
    inv_id = _post_invoice(seeded_client, ESCALATE_PAYLOAD)
    seeded_client.post(
        f"/api/v1/invoices/{inv_id}/comments",
        json={"body": "First comment"},
        headers={"X-Role": "priya"},
    )
    seeded_client.post(
        f"/api/v1/invoices/{inv_id}/comments",
        json={"body": "Second comment"},
        headers={"X-Role": "maya"},
    )
    resp = seeded_client.get(f"/api/v1/invoices/{inv_id}/comments")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 2
    assert items[0]["body"] == "First comment"
    assert items[1]["body"] == "Second comment"


def test_comment_on_missing_invoice_returns_404(seeded_client: TestClient) -> None:
    """Adding a comment to a non-existent invoice must return 404, not 500/IntegrityError."""
    resp = seeded_client.post(
        "/api/v1/invoices/inv-does-not-exist/comments",
        json={"body": "Hello"},
        headers={"X-Role": "priya"},
    )
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"]


def test_list_comments_on_missing_invoice_returns_404(seeded_client: TestClient) -> None:
    resp = seeded_client.get("/api/v1/invoices/inv-does-not-exist/comments")
    assert resp.status_code == 404


def test_list_comments_empty_for_new_invoice(seeded_client: TestClient) -> None:
    inv_id = _post_invoice(seeded_client, ESCALATE_PAYLOAD)
    resp = seeded_client.get(f"/api/v1/invoices/{inv_id}/comments")
    assert resp.status_code == 200
    assert resp.json() == []


# ---------------------------------------------------------------------------
# Reject action
# ---------------------------------------------------------------------------


def test_reject_sets_status_and_decision_fields(seeded_client: TestClient) -> None:
    inv_id = _post_invoice(seeded_client, ESCALATE_PAYLOAD)
    resp = seeded_client.post(
        f"/api/v1/invoices/{inv_id}/action",
        json={"action": "reject", "reason": "Duplicate invoice detected by reviewer"},
        headers={"X-Role": "priya"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "rejected"
    assert data["decided_by"] == "priya"
    assert data["decided_at"] is not None
    assert data["decision_reason"] == "Duplicate invoice detected by reviewer"


def test_reject_requires_reason(seeded_client: TestClient) -> None:
    inv_id = _post_invoice(seeded_client, ESCALATE_PAYLOAD)
    resp = seeded_client.post(
        f"/api/v1/invoices/{inv_id}/action",
        json={"action": "reject"},
        headers={"X-Role": "maya"},
    )
    assert resp.status_code == 422  # pydantic validation error


def test_approve_sets_decided_by(seeded_client: TestClient) -> None:
    inv_id = _post_invoice(seeded_client, ESCALATE_PAYLOAD)
    resp = seeded_client.post(
        f"/api/v1/invoices/{inv_id}/action",
        json={"action": "approve"},
        headers={"X-Role": "priya"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["decided_by"] == "priya"
    assert data["decided_at"] is not None
    assert data["decision_reason"] is not None


def test_route_sets_decided_fields(seeded_client: TestClient) -> None:
    inv_id = _post_invoice(seeded_client, ESCALATE_PAYLOAD)
    resp = seeded_client.post(
        f"/api/v1/invoices/{inv_id}/action",
        json={"action": "route"},
        # X-Role "priya" maps to "priya"; anything else maps to "maya" per security.py
        headers={"X-Role": "maya"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "routed"
    # "maya" is the default role for non-priya headers
    assert data["decided_by"] == "maya"
    assert data["decided_at"] is not None


def test_hold_sets_decided_fields(seeded_client: TestClient) -> None:
    inv_id = _post_invoice(seeded_client, ESCALATE_PAYLOAD)
    resp = seeded_client.post(
        f"/api/v1/invoices/{inv_id}/action",
        json={"action": "hold"},
        # "priya" is the only non-maya role recognized
        headers={"X-Role": "priya"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "held"
    assert data["decided_by"] == "priya"


# ---------------------------------------------------------------------------
# Soft-delete
# ---------------------------------------------------------------------------


def test_soft_deleted_invoice_excluded_from_list(
    client: TestClient, db: Session
) -> None:
    """An invoice with is_deleted=True must not appear in GET /invoices."""
    inv = Invoice(
        id="inv-to-delete",
        vendor="DeleteCo",
        amount=Decimal("100.00"),
        invoice_number="DEL-001",
        status="received",
        is_deleted=True,
    )
    db.add(inv)
    db.commit()

    resp = client.get("/api/v1/invoices")
    assert resp.status_code == 200
    ids = [i["id"] for i in resp.json()]
    assert "inv-to-delete" not in ids


def test_non_deleted_invoice_appears_in_list(client: TestClient, db: Session) -> None:
    """A normal invoice (is_deleted=False) must appear in GET /invoices."""
    inv = Invoice(
        id="inv-active",
        vendor="ActiveCo",
        amount=Decimal("200.00"),
        invoice_number="ACT-001",
        status="received",
        is_deleted=False,
    )
    db.add(inv)
    db.commit()

    resp = client.get("/api/v1/invoices")
    assert resp.status_code == 200
    ids = [i["id"] for i in resp.json()]
    assert "inv-active" in ids


# ---------------------------------------------------------------------------
# InvoiceOut — new fields present
# ---------------------------------------------------------------------------


def test_invoice_out_has_new_fields(client: TestClient, db: Session) -> None:
    """GET /invoices/{id} must include updated_at, decided_by, decided_at, decision_reason."""
    inv = Invoice(
        id="inv-fields",
        vendor="FieldCo",
        amount=Decimal("300.00"),
        invoice_number="FLD-001",
        status="received",
    )
    db.add(inv)
    db.commit()

    resp = client.get("/api/v1/invoices/inv-fields")
    assert resp.status_code == 200
    data = resp.json()
    assert "updated_at" in data
    assert "decided_by" in data
    assert "decided_at" in data
    assert "decision_reason" in data
    assert data["decided_by"] is None
    assert data["decided_at"] is None
    assert data["decision_reason"] is None
