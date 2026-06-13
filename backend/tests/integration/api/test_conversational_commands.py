"""Integration tests for conversational command dispatch.

These tests verify the full stack:
  MockClient.parse_command → conversation_agent.handle → DB

All tests use the MockClient (conftest forces it).
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models.invoice import Invoice
from app.db.models.organization import Organization
from app.db.models.purchase_order import PurchaseOrder
from app.db.models.vendor import Vendor
from app.repositories import invoice_repo
from tests.conftest import TEST_ORG_ID, TEST_ORG_NAME


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def cmd_db(db: Session) -> Session:
    """Seed a minimal dataset for command dispatch tests:

    Vendors:
      - Coolblue B.V. (approved)
      - Palmer LLC (approved)
      - Acme Corp (approved, for clearable invoices)

    POs:
      - po-cb-1: Coolblue B.V., $700.00
      - po-palmer-1: Palmer LLC, $200.00
      - po-acme-1: Acme Corp, $10000

    Invoices (received, unless noted):
      inv-cb-1   Coolblue B.V.  $80.00   received
      inv-cb-2   Coolblue B.V.  $120.00  received
      inv-cb-3   Coolblue B.V.  $45.00   received
      inv-pal-1  Palmer LLC     $60.00   received
      inv-pal-2  Palmer LLC     $90.00   received
      inv-other  Acme Corp      $200.00  received
      inv-needs1 Acme Corp      $30.00   needs    (escalated)
      inv-needs2 Palmer LLC     $40.00   needs    (escalated)
    """
    from app.core.config import get_settings

    settings = get_settings()

    # Ensure the test org row exists so FK constraints pass.
    if db.get(Organization, TEST_ORG_ID) is None:
        db.add(Organization(id=TEST_ORG_ID, name=TEST_ORG_NAME))
        db.flush()

    # Vendors
    for v_id, name in [
        ("v-cb", "Coolblue B.V."),
        ("v-palmer", "Palmer LLC"),
        ("v-acme", "Acme Corp"),
    ]:
        db.add(Vendor(id=v_id, canonical_name=name, status="approved", org_id=TEST_ORG_ID))

    # POs
    db.add(PurchaseOrder(id="po-cb-1", po_number="PO-CB-1", vendor="Coolblue B.V.", amount=Decimal("700"), org_id=TEST_ORG_ID))
    db.add(PurchaseOrder(id="po-palmer-1", po_number="PO-PALMER-1", vendor="Palmer LLC", amount=Decimal("200"), org_id=TEST_ORG_ID))
    db.add(PurchaseOrder(id="po-acme-1", po_number="PO-1", vendor="Acme Corp", amount=Decimal("10000"), org_id=TEST_ORG_ID))

    # Cleared history for cold-start check
    for i in range(settings.cold_start_n):
        db.add(Invoice(
            id=f"hist-cb-{i}", status="cleared", vendor="Coolblue B.V.",
            amount=Decimal("700"), invoice_number=f"HIST-CB-{i}",
            org_id=TEST_ORG_ID,
        ))
        db.add(Invoice(
            id=f"hist-pal-{i}", status="cleared", vendor="Palmer LLC",
            amount=Decimal("200"), invoice_number=f"HIST-PAL-{i}",
            org_id=TEST_ORG_ID,
        ))
        db.add(Invoice(
            id=f"hist-acme-{i}", status="cleared", vendor="Acme Corp",
            amount=Decimal("1000"), invoice_number=f"HIST-ACME-{i}",
            org_id=TEST_ORG_ID,
        ))

    # Received invoices
    db.add(Invoice(id="inv-cb-1", status="received", vendor="Coolblue B.V.", amount=Decimal("80.00"), invoice_number="CB-001", po_number="PO-CB-1", org_id=TEST_ORG_ID))
    db.add(Invoice(id="inv-cb-2", status="received", vendor="Coolblue B.V.", amount=Decimal("120.00"), invoice_number="CB-002", po_number="PO-CB-1", org_id=TEST_ORG_ID))
    db.add(Invoice(id="inv-cb-3", status="received", vendor="Coolblue B.V.", amount=Decimal("45.00"), invoice_number="CB-003", po_number="PO-CB-1", org_id=TEST_ORG_ID))
    db.add(Invoice(id="inv-pal-1", status="received", vendor="Palmer LLC", amount=Decimal("60.00"), invoice_number="PAL-001", po_number="PO-PALMER-1", org_id=TEST_ORG_ID))
    db.add(Invoice(id="inv-pal-2", status="received", vendor="Palmer LLC", amount=Decimal("90.00"), invoice_number="PAL-002", po_number="PO-PALMER-1", org_id=TEST_ORG_ID))
    db.add(Invoice(id="inv-other", status="received", vendor="Acme Corp", amount=Decimal("200.00"), invoice_number="ACME-001", po_number="PO-1", org_id=TEST_ORG_ID))

    # Escalated (needs) invoices
    db.add(Invoice(id="inv-needs1", status="needs", vendor="Acme Corp", amount=Decimal("30.00"), invoice_number="NEEDS-001", org_id=TEST_ORG_ID))
    db.add(Invoice(id="inv-needs2", status="needs", vendor="Palmer LLC", amount=Decimal("40.00"), invoice_number="NEEDS-002", org_id=TEST_ORG_ID))

    db.commit()
    return db


@pytest.fixture()
def cmd_client(client: TestClient, cmd_db: Session) -> TestClient:
    """TestClient with the cmd_db data already committed."""
    return client


# ---------------------------------------------------------------------------
# 1. process all invoices from Coolblue
# ---------------------------------------------------------------------------


def test_process_coolblue_only(cmd_client: TestClient, cmd_db: Session) -> None:
    """'process all invoices from Coolblue' should process only Coolblue received invoices."""
    resp = cmd_client.post(
        "/api/v1/chat",
        json={"message": "process all invoices from Coolblue"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "process_batch"
    result = data["result"]
    assert result is not None
    total_processed = result["queued"] + result["needs"] + result["blocked"]
    # 3 Coolblue received invoices should be processed
    assert total_processed == 3

    # Palmer and Acme received invoices must remain 'received'
    palmer_inv = invoice_repo.get(cmd_db, "inv-pal-1")
    assert palmer_inv is not None
    assert palmer_inv.status == "received"

    acme_inv = invoice_repo.get(cmd_db, "inv-other")
    assert acme_inv is not None
    assert acme_inv.status == "received"


# ---------------------------------------------------------------------------
# 2. review invoices under $100
# ---------------------------------------------------------------------------


def test_review_under_100_returns_list(cmd_client: TestClient) -> None:
    resp = cmd_client.post(
        "/api/v1/chat",
        json={"message": "review invoices under 100"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "list"
    result = data["result"]
    assert result is not None
    assert "list" in result
    # Every row amount must be < 100
    for row in result["list"]:
        assert row["amount"] is not None
        assert Decimal(row["amount"]) < Decimal("100"), (
            f"Expected amount < 100 but got {row['amount']} for {row['id']}"
        )


# ---------------------------------------------------------------------------
# 3. show all invoices from Palmer
# ---------------------------------------------------------------------------


def test_show_palmer_invoices(cmd_client: TestClient) -> None:
    resp = cmd_client.post(
        "/api/v1/chat",
        json={"message": "show all invoices from Palmer"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "list"
    result = data["result"]
    assert result is not None
    assert "list" in result
    assert len(result["list"]) > 0
    # All rows should be for Palmer LLC
    for row in result["list"]:
        assert row["vendor"] is not None
        assert "Palmer" in row["vendor"], f"Expected Palmer but got {row['vendor']}"


# ---------------------------------------------------------------------------
# 4. how many need review
# ---------------------------------------------------------------------------


def test_how_many_need_review(cmd_client: TestClient) -> None:
    resp = cmd_client.post(
        "/api/v1/chat",
        json={"message": "how many need review"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "aggregate"
    result = data["result"]
    assert result is not None
    assert "aggregate" in result
    # We seeded 2 needs invoices
    agg = result["aggregate"]
    assert agg["value"] == "2", f"Expected 2 needs invoices but got {agg['value']}"


# ---------------------------------------------------------------------------
# 5. approve all under $50 → bulk_confirm, no execution
# ---------------------------------------------------------------------------


def test_approve_under_50_bulk_confirm(cmd_client: TestClient, cmd_db: Session) -> None:
    resp = cmd_client.post(
        "/api/v1/chat",
        json={"message": "approve all under 50"},
        headers={"X-Role": "priya"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "bulk_confirm"
    result = data["result"]
    assert result is not None
    bulk = result["bulk"]
    assert bulk["action"] == "approve"
    # Invoices with amount < 50: inv-cb-3 ($45), inv-needs1 ($30), inv-needs2 ($40)
    assert bulk["count"] >= 3

    # No invoice should have been executed — all under-$50 received stay received
    inv_cb3 = invoice_repo.get(cmd_db, "inv-cb-3")
    assert inv_cb3 is not None
    assert inv_cb3.status == "received", (
        f"Expected received but got {inv_cb3.status} — approve must not execute"
    )


# ---------------------------------------------------------------------------
# 6. POST /invoices/bulk-action — confirm approve of needs invoices
# ---------------------------------------------------------------------------


def test_bulk_action_approve_needs_invoices(cmd_client: TestClient, cmd_db: Session) -> None:
    # The two needs invoices in our fixture
    ids = ["inv-needs1", "inv-needs2"]

    resp = cmd_client.post(
        "/api/v1/invoices/bulk-action",
        json={"ids": ids, "action": "approve"},
        headers={"X-Role": "priya"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["applied"] == 2
    assert len(data["results"]) == 2

    # Both invoices should now be queued
    for item in data["results"]:
        assert item["status"] == "queued", (
            f"Expected queued but got {item['status']} for {item['id']}"
        )


# ---------------------------------------------------------------------------
# Existing tests still pass: process today's invoices
# ---------------------------------------------------------------------------


def test_process_today_still_works(cmd_client: TestClient) -> None:
    resp = cmd_client.post(
        "/api/v1/chat",
        json={"message": "process today's invoices"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "process_batch"
    result = data["result"]
    assert result is not None
    assert "queued" in result
    assert "needs" in result
    assert "blocked" in result


# ---------------------------------------------------------------------------
# Existing tests: review invoice <id> (single review)
# ---------------------------------------------------------------------------


def test_review_invoice_by_id_still_works(cmd_client: TestClient) -> None:
    resp = cmd_client.post(
        "/api/v1/chat",
        json={"message": "review invoice CB-001"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "review_invoice"
    result = data["result"]
    assert result is not None
    assert result["invoice"]["invoice_number"] == "CB-001"


# ---------------------------------------------------------------------------
# Existing tests: smalltalk
# ---------------------------------------------------------------------------


def test_smalltalk_still_works(cmd_client: TestClient) -> None:
    resp = cmd_client.post(
        "/api/v1/chat",
        json={"message": "hello there"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "smalltalk"
    assert data["result"] is None


# ---------------------------------------------------------------------------
# "to be processed" must count RECEIVED (pending), not queued
# ---------------------------------------------------------------------------


def test_count_to_be_processed_counts_received(cmd_client: TestClient) -> None:
    resp = cmd_client.post(
        "/api/v1/chat", json={"message": "how many need to be processed?"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "aggregate"
    assert data["result"]["aggregate"]["value"] == "6"  # 6 received in the fixture
    assert "waiting to be processed" in data["reply"]


def test_count_need_review_counts_needs(cmd_client: TestClient) -> None:
    resp = cmd_client.post("/api/v1/chat", json={"message": "how many need review?"})
    data = resp.json()
    assert data["result"]["aggregate"]["value"] == "2"  # 2 needs in the fixture
    assert "need review" in data["reply"]
