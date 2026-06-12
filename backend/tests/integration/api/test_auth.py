"""Integration tests for the /api/v1/auth endpoints and API-wide auth gating."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.main import app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SIGNUP_URL = "/api/v1/auth/signup"
_VERIFY_URL = "/api/v1/auth/verify"
_LOGIN_URL = "/api/v1/auth/login"
_ME_URL = "/api/v1/auth/me"
_INVOICES_URL = "/api/v1/invoices"
_MEMBERS_URL = "/api/v1/auth/org/members"
_PENDING_URL = "/api/v1/auth/org/pending"
_VERIFY_USER_URL = "/api/v1/auth/org/verify-user"

_ORG_NAME_A = "Acme Corp"
_ORG_NAME_B = "Beta Corp"


def _signup(
    client: TestClient,
    email: str = "alice@example.com",
    password: str = "secret123",
    org_name: str = _ORG_NAME_A,
) -> object:
    return client.post(_SIGNUP_URL, json={"email": email, "password": password, "org_name": org_name})


def _full_flow_founder(
    raw_client: TestClient,
    email: str = "alice@example.com",
    password: str = "secret123",
    org_name: str = _ORG_NAME_A,
) -> str:
    """Signup as org founder (auto-verified) → login; returns access token."""
    r = raw_client.post(_SIGNUP_URL, json={"email": email, "password": password, "org_name": org_name})
    assert r.status_code == 201, r.json()
    assert r.json()["status"] == "active"

    r2 = raw_client.post(_LOGIN_URL, json={"email": email, "password": password})
    assert r2.status_code == 200, r2.json()
    return str(r2.json()["access_token"])


# ---------------------------------------------------------------------------
# Fixture: a raw TestClient that does NOT override get_current_user so we can
# test the real auth flow.  Still overrides get_db + get_llm from conftest,
# but we recreate it here pointing at the same engine.
# ---------------------------------------------------------------------------

@pytest.fixture
def raw_client(client: TestClient) -> TestClient:  # type: ignore[return]
    """Remove the get_current_user override so auth is fully exercised."""
    app.dependency_overrides.pop(get_current_user, None)
    try:
        yield client  # type: ignore[misc]
    finally:
        pass


# ---------------------------------------------------------------------------
# Signup — founder (new org) creates admin + active account
# ---------------------------------------------------------------------------


def test_signup_founder_returns_201_and_active(raw_client: TestClient) -> None:
    resp = _signup(raw_client, "bob@example.com", "pass1234")
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "active"
    assert "message" in data
    # No verify_token in the new schema
    assert "verify_token" not in data


def test_signup_founder_user_is_verified(raw_client: TestClient, db: Session) -> None:
    _signup(raw_client, "carol@example.com", "pass1234")
    from app.repositories import user_repo
    user = user_repo.get_by_email(db, "carol@example.com")
    assert user is not None
    assert user.is_verified is True
    assert user.role == "admin"


def test_signup_founder_org_is_created(raw_client: TestClient, db: Session) -> None:
    _signup(raw_client, "founder@example.com", "pass1234", org_name="Brand New Org")
    from app.repositories import org_repo
    org = org_repo.get_by_name(db, "Brand New Org")
    assert org is not None


# ---------------------------------------------------------------------------
# Signup — second user joins existing org (pending)
# ---------------------------------------------------------------------------


def test_signup_member_returns_pending(raw_client: TestClient) -> None:
    _signup(raw_client, "founder@example.com", "pass1234", org_name=_ORG_NAME_A)
    resp = _signup(raw_client, "member@example.com", "pass1234", org_name=_ORG_NAME_A)
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "pending"


def test_signup_member_user_is_not_verified(raw_client: TestClient, db: Session) -> None:
    _signup(raw_client, "founder@example.com", "pass1234", org_name=_ORG_NAME_A)
    _signup(raw_client, "member@example.com", "pass1234", org_name=_ORG_NAME_A)
    from app.repositories import user_repo
    member = user_repo.get_by_email(db, "member@example.com")
    assert member is not None
    assert member.is_verified is False
    assert member.role == "member"


def test_duplicate_email_signup_returns_409(raw_client: TestClient) -> None:
    _signup(raw_client, "dup@example.com", "pass1234")
    resp = _signup(raw_client, "dup@example.com", "pass1234")
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


def test_login_before_admin_approval_returns_403(raw_client: TestClient) -> None:
    _signup(raw_client, "founder@example.com", "pass1234", org_name=_ORG_NAME_A)
    _signup(raw_client, "pending@example.com", "pass1234", org_name=_ORG_NAME_A)
    resp = raw_client.post(_LOGIN_URL, json={"email": "pending@example.com", "password": "pass1234"})
    assert resp.status_code == 403
    assert "pending" in resp.json()["detail"].lower()


def test_login_after_founder_signup_returns_token(raw_client: TestClient) -> None:
    _signup(raw_client, "alice@example.com", "pass1234")
    resp = raw_client.post(_LOGIN_URL, json={"email": "alice@example.com", "password": "pass1234"})
    assert resp.status_code == 200
    assert len(resp.json()["access_token"]) > 20


def test_login_bad_password_returns_401(raw_client: TestClient) -> None:
    _signup(raw_client, "badpw@example.com", "correct")
    resp = raw_client.post(_LOGIN_URL, json={"email": "badpw@example.com", "password": "wrong"})
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /auth/me — returns org + role
# ---------------------------------------------------------------------------


def test_get_me_with_valid_token(raw_client: TestClient) -> None:
    token = _full_flow_founder(raw_client, "me@example.com", org_name="MeOrg")
    resp = raw_client.get(_ME_URL, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "me@example.com"
    assert data["is_verified"] is True
    assert data["role"] == "admin"
    assert data["org_id"] is not None
    assert data["org_name"] == "MeOrg"


def test_get_me_without_token_returns_401(raw_client: TestClient) -> None:
    resp = raw_client.get(_ME_URL)
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Admin endpoints: list members / pending / verify-user
# ---------------------------------------------------------------------------


def test_admin_list_members(raw_client: TestClient) -> None:
    token = _full_flow_founder(raw_client, "admin@example.com", org_name="AdminOrg")
    resp = raw_client.get(_MEMBERS_URL, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    members = resp.json()
    assert isinstance(members, list)
    emails = [m["email"] for m in members]
    assert "admin@example.com" in emails


def test_admin_list_pending(raw_client: TestClient) -> None:
    token = _full_flow_founder(raw_client, "admin@example.com", org_name="PendingOrg")
    # Add a pending member
    _signup(raw_client, "pending@example.com", "pass1234", org_name="PendingOrg")
    resp = raw_client.get(_PENDING_URL, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    pending = resp.json()
    assert any(m["email"] == "pending@example.com" for m in pending)


def test_admin_verify_user(raw_client: TestClient, db: Session) -> None:
    token = _full_flow_founder(raw_client, "admin@example.com", org_name="VerifyOrg")
    _signup(raw_client, "toverify@example.com", "pass1234", org_name="VerifyOrg")

    from app.repositories import user_repo
    target = user_repo.get_by_email(db, "toverify@example.com")
    assert target is not None
    assert target.is_verified is False

    resp = raw_client.post(
        _VERIFY_USER_URL,
        json={"user_id": target.id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_verified"] is True

    # Can now log in
    login_resp = raw_client.post(_LOGIN_URL, json={"email": "toverify@example.com", "password": "pass1234"})
    assert login_resp.status_code == 200


def test_non_admin_cannot_verify_user(raw_client: TestClient, db: Session) -> None:
    """A member (non-admin) cannot call verify-user."""
    # Create an org with a founder
    admin_token = _full_flow_founder(raw_client, "admin@example.com", org_name="MixedOrg")
    # Founder signs up two members
    _signup(raw_client, "member1@example.com", "pass1234", org_name="MixedOrg")
    _signup(raw_client, "member2@example.com", "pass1234", org_name="MixedOrg")

    # Admin verifies member1 so they can log in
    from app.repositories import user_repo
    m1 = user_repo.get_by_email(db, "member1@example.com")
    assert m1 is not None
    raw_client.post(
        _VERIFY_USER_URL,
        json={"user_id": m1.id},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # member1 (role=member) tries to verify member2
    login_m1 = raw_client.post(_LOGIN_URL, json={"email": "member1@example.com", "password": "pass1234"})
    m1_token = login_m1.json()["access_token"]

    m2 = user_repo.get_by_email(db, "member2@example.com")
    assert m2 is not None
    resp = raw_client.post(
        _VERIFY_USER_URL,
        json={"user_id": m2.id},
        headers={"Authorization": f"Bearer {m1_token}"},
    )
    assert resp.status_code == 403


def test_cross_org_verify_user_returns_403(raw_client: TestClient, db: Session) -> None:
    """Admin from org A cannot verify a user in org B."""
    admin_a_token = _full_flow_founder(raw_client, "adminA@example.com", org_name="OrgA")
    # Create org B with its own founder
    _full_flow_founder(raw_client, "adminB@example.com", org_name="OrgB")
    # Add a member to org B
    r_mb = _signup(raw_client, "memberB@example.com", "pass1234", org_name="OrgB")
    assert r_mb.status_code == 201

    # Use the signup response to get the user_id directly (avoids cross-session visibility issues)
    # by querying via a fresh session
    from sqlalchemy import text

    row = db.execute(
        text("SELECT id FROM users WHERE email = 'memberb@example.com'")
    ).fetchone()
    assert row is not None, "memberB user not found in DB"
    mb_id = row[0]

    resp = raw_client.post(
        _VERIFY_USER_URL,
        json={"user_id": mb_id},
        headers={"Authorization": f"Bearer {admin_a_token}"},
    )
    assert resp.status_code == 403


def test_members_endpoint_requires_admin(raw_client: TestClient, db: Session) -> None:
    admin_token = _full_flow_founder(raw_client, "admin@example.com", org_name="AuthOrg")
    _signup(raw_client, "member@example.com", "pass1234", org_name="AuthOrg")

    from app.repositories import user_repo
    m = user_repo.get_by_email(db, "member@example.com")
    assert m is not None
    # Verify member so they can log in
    raw_client.post(
        _VERIFY_USER_URL,
        json={"user_id": m.id},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    member_token = raw_client.post(
        _LOGIN_URL, json={"email": "member@example.com", "password": "pass1234"}
    ).json()["access_token"]

    resp = raw_client.get(_MEMBERS_URL, headers={"Authorization": f"Bearer {member_token}"})
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Protected routes — gating
# ---------------------------------------------------------------------------


def test_protected_route_without_token_returns_401(raw_client: TestClient) -> None:
    """GET /api/v1/invoices without a token must return 401."""
    resp = raw_client.get(_INVOICES_URL)
    assert resp.status_code == 401


def test_protected_route_with_valid_token_returns_200(raw_client: TestClient) -> None:
    """GET /api/v1/invoices with a valid founder token must return 200."""
    token = _full_flow_founder(raw_client, "inv@example.com", org_name="InvOrg")
    resp = raw_client.get(_INVOICES_URL, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ---------------------------------------------------------------------------
# Legacy verify endpoint — backward compat
# ---------------------------------------------------------------------------


def test_verify_with_bad_token_returns_400(raw_client: TestClient) -> None:
    resp = raw_client.post(_VERIFY_URL, json={"token": "totally-invalid-token"})
    assert resp.status_code == 400
