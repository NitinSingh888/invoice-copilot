from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models.correction import Correction


# ---------------------------------------------------------------------------
# Fixtures that seed Corrections into db before requests
# ---------------------------------------------------------------------------


@pytest.fixture()
def client_with_corrections(client: TestClient, db: Session) -> TestClient:
    """client with 3 Correction rows committed to the test DB."""
    from app.db.models.invoice import Invoice

    # Parent invoices must exist before corrections due to FK constraint.
    for i in range(3):
        db.add(Invoice(id=f"inv-seed-{i}", vendor="Acme Corp", amount=Decimal("100")))
    db.flush()
    for i, over_pct in enumerate(["0.06", "0.04", "0.07"]):
        db.add(
            Correction(
                id=f"corr-seed-{i}",
                invoice_id=f"inv-seed-{i}",
                vendor="Acme Corp",
                finding_code="OVER_TOLERANCE",
                user_action="route",
                over_pct=Decimal(over_pct),
            )
        )
    db.commit()
    return client


# ---------------------------------------------------------------------------
# POST /rules/propose — with corrections
# ---------------------------------------------------------------------------


def test_propose_rule_returns_proposal(client_with_corrections: TestClient) -> None:
    resp = client_with_corrections.post("/api/v1/rules/propose")
    assert resp.status_code == 200
    data = resp.json()
    assert Decimal(str(data["threshold_pct"])) == Decimal("0.08")
    assert data["route"] == "Priya"
    assert data["candidate"]["vendor"] == "Acme Corp"


# ---------------------------------------------------------------------------
# POST /rules/propose — no corrections → 204
# ---------------------------------------------------------------------------


def test_propose_rule_no_corrections_returns_204(client: TestClient) -> None:
    resp = client.post("/api/v1/rules/propose")
    assert resp.status_code == 204


# ---------------------------------------------------------------------------
# POST /rules/activate → 201
# ---------------------------------------------------------------------------


def test_activate_rule(client_with_corrections: TestClient) -> None:
    resp = client_with_corrections.post(
        "/api/v1/rules/activate",
        json={"threshold_pct": "0.08", "route": "Priya"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "active"
    assert Decimal(str(data["max_over_pct"])) == Decimal("0.08")
    assert data["route"] == "Priya"
    # Induction agent should populate reasoning_note with non-empty LLM explanation
    assert data["reasoning_note"] is not None
    assert len(data["reasoning_note"]) > 0


# ---------------------------------------------------------------------------
# GET /rules — lists active rule after activation
# ---------------------------------------------------------------------------


def test_list_rules_after_activate(client_with_corrections: TestClient) -> None:
    client_with_corrections.post(
        "/api/v1/rules/activate",
        json={"threshold_pct": "0.08", "route": "Priya"},
    )
    resp = client_with_corrections.get("/api/v1/rules")
    assert resp.status_code == 200
    rules = resp.json()
    assert len(rules) == 1
    assert rules[0]["status"] == "active"


# ---------------------------------------------------------------------------
# PATCH /rules/{id} — disable rule
# ---------------------------------------------------------------------------


def test_patch_rule_disable(client_with_corrections: TestClient) -> None:
    activate_resp = client_with_corrections.post(
        "/api/v1/rules/activate",
        json={"threshold_pct": "0.08", "route": "Priya"},
    )
    assert activate_resp.status_code == 201
    rule_id = activate_resp.json()["id"]

    resp = client_with_corrections.patch(
        f"/api/v1/rules/{rule_id}", json={"status": "disabled"}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "disabled"


# ---------------------------------------------------------------------------
# PATCH /rules/{id} — missing rule → 404
# ---------------------------------------------------------------------------


def test_patch_rule_not_found(client: TestClient) -> None:
    resp = client.patch("/api/v1/rules/does-not-exist", json={"status": "disabled"})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /rules — manual rule creation
# ---------------------------------------------------------------------------


def test_create_rule_returns_201_active(client: TestClient) -> None:
    """POST /rules creates an active rule that appears in GET /rules."""
    resp = client.post(
        "/api/v1/rules",
        json={"vendor": "Beta LLC", "finding_code": "OVER_TOLERANCE", "route": "Priya"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "active"
    assert data["vendor"] == "Beta LLC"
    assert data["finding_code"] == "OVER_TOLERANCE"
    assert data["route"] == "Priya"
    assert data["source_correction_ids"] == []
    assert data["reasoning_note"] is not None
    assert "manually" in data["reasoning_note"]

    # Should appear in GET /rules
    list_resp = client.get("/api/v1/rules")
    assert list_resp.status_code == 200
    ids = [r["id"] for r in list_resp.json()]
    assert data["id"] in ids


def test_create_rule_finding_code_defaults_to_over_tolerance(client: TestClient) -> None:
    """Omitting finding_code defaults to OVER_TOLERANCE."""
    resp = client.post(
        "/api/v1/rules",
        json={"vendor": "Gamma Inc", "route": "approve"},
    )
    assert resp.status_code == 201
    assert resp.json()["finding_code"] == "OVER_TOLERANCE"


def test_create_rule_supersedes_prior_active_same_vendor_and_code(
    client: TestClient,
) -> None:
    """A second POST for the same (vendor, finding_code) supersedes the first."""
    payload = {"vendor": "Delta Co", "finding_code": "OVER_TOLERANCE", "route": "hold"}

    first_resp = client.post("/api/v1/rules", json=payload)
    assert first_resp.status_code == 201
    first_id = first_resp.json()["id"]

    second_resp = client.post("/api/v1/rules", json=payload)
    assert second_resp.status_code == 201
    second_id = second_resp.json()["id"]

    assert first_id != second_id

    all_rules = {r["id"]: r for r in client.get("/api/v1/rules").json()}
    assert all_rules[first_id]["status"] == "disabled"
    assert all_rules[second_id]["status"] == "active"


def test_create_rule_different_finding_code_coexists(client: TestClient) -> None:
    """Two rules for the same vendor but different finding_codes both stay active."""
    client.post(
        "/api/v1/rules",
        json={"vendor": "Epsilon Ltd", "finding_code": "OVER_TOLERANCE", "route": "Priya"},
    )
    client.post(
        "/api/v1/rules",
        json={"vendor": "Epsilon Ltd", "finding_code": "DUPLICATE_SUSPECT", "route": "hold"},
    )

    active_rules = [
        r
        for r in client.get("/api/v1/rules").json()
        if r["vendor"] == "Epsilon Ltd" and r["status"] == "active"
    ]
    codes = {r["finding_code"] for r in active_rules}
    assert codes == {"OVER_TOLERANCE", "DUPLICATE_SUSPECT"}
