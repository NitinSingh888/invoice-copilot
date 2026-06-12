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


def _signup(client: TestClient, email: str = "alice@example.com", password: str = "secret123") -> dict:  # type: ignore[type-arg]
    resp = client.post(_SIGNUP_URL, json={"email": email, "password": password})
    return resp


def _full_flow(raw_client: TestClient, email: str = "alice@example.com", password: str = "secret123") -> str:
    """Signup → verify → login; returns the access token."""
    r = raw_client.post(_SIGNUP_URL, json={"email": email, "password": password})
    assert r.status_code == 201
    verify_token = r.json()["verify_token"]

    r2 = raw_client.post(_VERIFY_URL, json={"token": verify_token})
    assert r2.status_code == 200

    r3 = raw_client.post(_LOGIN_URL, json={"email": email, "password": password})
    assert r3.status_code == 200
    return str(r3.json()["access_token"])


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
        # Restore override for subsequent tests — conftest teardown also clears it
        # but being explicit is safer.
        pass


# ---------------------------------------------------------------------------
# Signup
# ---------------------------------------------------------------------------


def test_signup_returns_201_and_verify_token(raw_client: TestClient) -> None:
    resp = raw_client.post(_SIGNUP_URL, json={"email": "bob@example.com", "password": "pass1234"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["message"] == "Verify your email to activate your account."
    assert len(data["verify_token"]) > 10


def test_signup_user_is_unverified(raw_client: TestClient, db: Session) -> None:
    resp = raw_client.post(_SIGNUP_URL, json={"email": "carol@example.com", "password": "pass1234"})
    assert resp.status_code == 201
    from app.repositories import user_repo
    user = user_repo.get_by_email(db, "carol@example.com")
    assert user is not None
    assert user.is_verified is False


def test_duplicate_signup_returns_409(raw_client: TestClient) -> None:
    raw_client.post(_SIGNUP_URL, json={"email": "dup@example.com", "password": "pass1234"})
    resp = raw_client.post(_SIGNUP_URL, json={"email": "dup@example.com", "password": "pass1234"})
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# Login before verification → 403
# ---------------------------------------------------------------------------


def test_login_before_verify_returns_403(raw_client: TestClient) -> None:
    raw_client.post(_SIGNUP_URL, json={"email": "early@example.com", "password": "pass1234"})
    resp = raw_client.post(_LOGIN_URL, json={"email": "early@example.com", "password": "pass1234"})
    assert resp.status_code == 403
    assert "not verified" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Verify with token → ok
# ---------------------------------------------------------------------------


def test_verify_with_valid_token(raw_client: TestClient) -> None:
    r = raw_client.post(_SIGNUP_URL, json={"email": "verify@example.com", "password": "pass1234"})
    token = r.json()["verify_token"]
    resp = raw_client.post(_VERIFY_URL, json={"token": token})
    assert resp.status_code == 200
    assert resp.json() == {"verified": True}


def test_verify_with_bad_token_returns_400(raw_client: TestClient) -> None:
    resp = raw_client.post(_VERIFY_URL, json={"token": "totally-invalid-token"})
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Login after verify → 200 + token
# ---------------------------------------------------------------------------


def test_login_after_verify_returns_token(raw_client: TestClient) -> None:
    token = _full_flow(raw_client, "logintest@example.com")
    assert len(token) > 20


def test_login_bad_password_returns_401(raw_client: TestClient) -> None:
    r = raw_client.post(_SIGNUP_URL, json={"email": "badpw@example.com", "password": "correct"})
    tok = r.json()["verify_token"]
    raw_client.post(_VERIFY_URL, json={"token": tok})
    resp = raw_client.post(_LOGIN_URL, json={"email": "badpw@example.com", "password": "wrong"})
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /auth/me with token
# ---------------------------------------------------------------------------


def test_get_me_with_valid_token(raw_client: TestClient) -> None:
    access_token = _full_flow(raw_client, "me@example.com")
    resp = raw_client.get(_ME_URL, headers={"Authorization": f"Bearer {access_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "me@example.com"
    assert data["is_verified"] is True


def test_get_me_without_token_returns_401(raw_client: TestClient) -> None:
    resp = raw_client.get(_ME_URL)
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Protected routes — gating
# ---------------------------------------------------------------------------


def test_protected_route_without_token_returns_401(raw_client: TestClient) -> None:
    """GET /api/v1/invoices without a token must return 401."""
    resp = raw_client.get(_INVOICES_URL)
    assert resp.status_code == 401


def test_protected_route_with_valid_token_returns_200(raw_client: TestClient) -> None:
    """GET /api/v1/invoices with a valid token must return 200."""
    access_token = _full_flow(raw_client, "inv@example.com")
    resp = raw_client.get(_INVOICES_URL, headers={"Authorization": f"Bearer {access_token}"})
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
