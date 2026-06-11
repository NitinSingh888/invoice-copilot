"""Integration tests for the review_invoice chat intent.

These tests seed the full demo dataset (all vendors, POs, invoices) and run the
batch first so that invoices have verdicts and statuses.  Then they exercise
the three review_invoice paths:

  1. "review cyberdyne" → vendor-substring lookup → UNKNOWN_VENDOR + MISSING_PO
  2. "show INV-4502"   → direct id lookup → blocked, DUPLICATE_EXACT
  3. "review zzz nonexistent" → not_found
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.seed import seed


@pytest.fixture()
def demo_processed_client(client: TestClient, db: Session) -> TestClient:
    """Seed the full demo dataset and run the batch so invoices have verdicts."""
    seed(db, force=True)
    db.commit()

    # Run the batch via the chat endpoint to assign verdicts/statuses
    resp = client.post("/api/v1/chat", json={"message": "process today's invoices"})
    assert resp.status_code == 200, f"batch failed: {resp.text}"
    return client


# ---------------------------------------------------------------------------
# 1. review cyberdyne → vendor lookup, UNKNOWN_VENDOR + MISSING_PO
# ---------------------------------------------------------------------------


def test_review_cyberdyne_intent(demo_processed_client: TestClient) -> None:
    resp = demo_processed_client.post(
        "/api/v1/chat",
        json={"message": "review cyberdyne invoice"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "review_invoice"


def test_review_cyberdyne_vendor(demo_processed_client: TestClient) -> None:
    resp = demo_processed_client.post(
        "/api/v1/chat",
        json={"message": "review cyberdyne invoice"},
    )
    result = resp.json()["result"]
    assert result is not None
    assert result["invoice"]["vendor"] == "Cyberdyne Systems"


def test_review_cyberdyne_findings_unknown_vendor(demo_processed_client: TestClient) -> None:
    resp = demo_processed_client.post(
        "/api/v1/chat",
        json={"message": "review cyberdyne invoice"},
    )
    result = resp.json()["result"]
    codes = [f["code"] for f in result["findings"]]
    assert "UNKNOWN_VENDOR" in codes


def test_review_cyberdyne_findings_missing_po(demo_processed_client: TestClient) -> None:
    resp = demo_processed_client.post(
        "/api/v1/chat",
        json={"message": "review cyberdyne invoice"},
    )
    result = resp.json()["result"]
    codes = [f["code"] for f in result["findings"]]
    assert "MISSING_PO" in codes


# ---------------------------------------------------------------------------
# 2. show INV-4502 → direct id lookup, blocked + DUPLICATE_EXACT
# ---------------------------------------------------------------------------


def test_show_inv4502_intent(demo_processed_client: TestClient) -> None:
    resp = demo_processed_client.post(
        "/api/v1/chat",
        json={"message": "show INV-4502"},
    )
    assert resp.status_code == 200
    assert resp.json()["intent"] == "review_invoice"


def test_show_inv4502_status_blocked(demo_processed_client: TestClient) -> None:
    resp = demo_processed_client.post(
        "/api/v1/chat",
        json={"message": "show INV-4502"},
    )
    result = resp.json()["result"]
    assert result is not None
    assert result["invoice"]["status"] == "blocked"


def test_show_inv4502_findings_duplicate_exact(demo_processed_client: TestClient) -> None:
    resp = demo_processed_client.post(
        "/api/v1/chat",
        json={"message": "show INV-4502"},
    )
    result = resp.json()["result"]
    codes = [f["code"] for f in result["findings"]]
    assert "DUPLICATE_EXACT" in codes


def test_show_inv4502_has_summary(demo_processed_client: TestClient) -> None:
    resp = demo_processed_client.post(
        "/api/v1/chat",
        json={"message": "show INV-4502"},
    )
    result = resp.json()["result"]
    assert isinstance(result["summary"], str)
    assert len(result["summary"]) > 0


# ---------------------------------------------------------------------------
# 3. review zzz nonexistent → not_found
# ---------------------------------------------------------------------------


def test_review_nonexistent_not_found(demo_processed_client: TestClient) -> None:
    resp = demo_processed_client.post(
        "/api/v1/chat",
        json={"message": "review zzz nonexistent vendor invoice"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "review_invoice"
    result = data["result"]
    assert result is not None
    assert result.get("not_found") is True
