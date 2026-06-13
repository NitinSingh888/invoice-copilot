from __future__ import annotations

from decimal import Decimal

from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.db.models.user import User
from app.main import app
from tests.conftest import TEST_ORG_ID


def test_get_policy_returns_default(client: TestClient) -> None:
    resp = client.get("/api/v1/policy")
    assert resp.status_code == 200
    data = resp.json()
    assert data["auto_approve_enabled"] is True
    assert Decimal(data["auto_approve_threshold"]) == Decimal("100")


def test_admin_can_update_policy(client: TestClient) -> None:
    resp = client.patch(
        "/api/v1/policy",
        json={"auto_approve_threshold": "250", "auto_approve_enabled": False},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["auto_approve_enabled"] is False
    assert Decimal(data["auto_approve_threshold"]) == Decimal("250")
    # Persisted
    again = client.get("/api/v1/policy").json()
    assert Decimal(again["auto_approve_threshold"]) == Decimal("250")


def test_negative_threshold_rejected(client: TestClient) -> None:
    resp = client.patch("/api/v1/policy", json={"auto_approve_threshold": "-5"})
    assert resp.status_code == 422


def test_member_cannot_update_policy(client: TestClient) -> None:
    member = User(
        id="usr-member-001",
        email="member@example.com",
        password_hash="",
        is_verified=True,
        verification_token=None,
        org_id=TEST_ORG_ID,
        role="member",
    )
    app.dependency_overrides[get_current_user] = lambda: member
    try:
        resp = client.patch("/api/v1/policy", json={"auto_approve_threshold": "5"})
        assert resp.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)
