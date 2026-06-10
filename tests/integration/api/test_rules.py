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
