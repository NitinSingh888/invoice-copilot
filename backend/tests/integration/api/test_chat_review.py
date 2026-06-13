"""Integration tests for the review_invoice chat intent.

These tests seed the full real-invoice demo dataset and run the batch first so
that invoices have verdicts and statuses.  Then they exercise the three
review_invoice paths:

  1. "review oyo" → vendor-substring lookup → UNKNOWN_VENDOR + MISSING_PO
  2. "review saeco" → vendor lookup → blocked, DUPLICATE_EXACT
  3. "review zzz nonexistent" → not_found
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models.organization import Organization
from app.seed import seed_org
from tests.conftest import TEST_ORG_ID, TEST_ORG_NAME


@pytest.fixture()
def demo_processed_client(client: TestClient, db: Session) -> TestClient:
    """Seed the full demo dataset (into TEST_ORG_ID) and run the batch so invoices
    have verdicts."""
    # Ensure the test org row exists
    if db.get(Organization, TEST_ORG_ID) is None:
        db.add(Organization(id=TEST_ORG_ID, name=TEST_ORG_NAME))
        db.flush()

    seed_org(db, TEST_ORG_ID)
    db.commit()

    # Run the batch via the chat endpoint to assign verdicts/statuses
    resp = client.post("/api/v1/chat", json={"message": "process today's invoices"})
    assert resp.status_code == 200, f"batch failed: {resp.text}"
    return client


# ---------------------------------------------------------------------------
# 1. review an unknown-vendor invoice (Daniel Group) → UNKNOWN_VENDOR
#    and an approved-but-no-PO invoice (Carter Inc) → MISSING_PO
# ---------------------------------------------------------------------------


def test_review_unknown_vendor_intent(demo_processed_client: TestClient) -> None:
    resp = demo_processed_client.post(
        "/api/v1/chat",
        json={"message": "review Daniel Group invoice"},
    )
    assert resp.status_code == 200
    assert resp.json()["intent"] == "review_invoice"


def test_review_unknown_vendor_resolves(demo_processed_client: TestClient) -> None:
    resp = demo_processed_client.post(
        "/api/v1/chat",
        json={"message": "review Daniel Group invoice"},
    )
    result = resp.json()["result"]
    assert result is not None
    assert result["invoice"]["vendor"] == "Daniel Group"


def test_review_unknown_vendor_findings(demo_processed_client: TestClient) -> None:
    resp = demo_processed_client.post(
        "/api/v1/chat",
        json={"message": "review Daniel Group invoice"},
    )
    result = resp.json()["result"]
    codes = [f["code"] for f in result["findings"]]
    assert "UNKNOWN_VENDOR" in codes


def test_review_missing_po_findings(demo_processed_client: TestClient) -> None:
    resp = demo_processed_client.post(
        "/api/v1/chat",
        json={"message": "review Carter Inc invoice"},
    )
    result = resp.json()["result"]
    codes = [f["code"] for f in result["findings"]]
    assert "MISSING_PO" in codes


# ---------------------------------------------------------------------------
# 2. review saeco → vendor lookup → blocked + DUPLICATE_EXACT
# ---------------------------------------------------------------------------


def test_show_saeco_intent(demo_processed_client: TestClient) -> None:
    resp = demo_processed_client.post(
        "/api/v1/chat",
        json={"message": "review saeco invoice"},
    )
    assert resp.status_code == 200
    assert resp.json()["intent"] == "review_invoice"


def test_show_saeco_status_blocked(demo_processed_client: TestClient) -> None:
    resp = demo_processed_client.post(
        "/api/v1/chat",
        json={"message": "review saeco invoice"},
    )
    result = resp.json()["result"]
    assert result is not None
    assert result["invoice"]["status"] == "blocked"


def test_show_saeco_findings_duplicate_exact(demo_processed_client: TestClient) -> None:
    resp = demo_processed_client.post(
        "/api/v1/chat",
        json={"message": "review saeco invoice"},
    )
    result = resp.json()["result"]
    codes = [f["code"] for f in result["findings"]]
    assert "DUPLICATE_EXACT" in codes


def test_show_saeco_has_summary(demo_processed_client: TestClient) -> None:
    resp = demo_processed_client.post(
        "/api/v1/chat",
        json={"message": "review saeco invoice"},
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
