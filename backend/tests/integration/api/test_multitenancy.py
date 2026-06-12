"""Tests proving org isolation — a user from org A cannot see org B's data."""
from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models.invoice import Invoice
from app.db.models.organization import Organization
from app.main import app

_SIGNUP_URL = "/api/v1/auth/signup"
_LOGIN_URL = "/api/v1/auth/login"
_INVOICES_URL = "/api/v1/invoices"
_ME_URL = "/api/v1/auth/me"


def _make_two_orgs(
    raw_client: TestClient, db: Session
) -> tuple[str, str, str, str]:
    """Create org A and org B, each with a founder.

    Returns (token_a, org_id_a, token_b, org_id_b).
    """
    # Org A
    raw_client.post(_SIGNUP_URL, json={"email": "userA@example.com", "password": "pass", "org_name": "OrgA"})
    resp_a = raw_client.post(_LOGIN_URL, json={"email": "userA@example.com", "password": "pass"})
    token_a = resp_a.json()["access_token"]
    me_a = raw_client.get(_ME_URL, headers={"Authorization": f"Bearer {token_a}"}).json()
    org_id_a = me_a["org_id"]

    # Org B
    raw_client.post(_SIGNUP_URL, json={"email": "userB@example.com", "password": "pass", "org_name": "OrgB"})
    resp_b = raw_client.post(_LOGIN_URL, json={"email": "userB@example.com", "password": "pass"})
    token_b = resp_b.json()["access_token"]
    me_b = raw_client.get(_ME_URL, headers={"Authorization": f"Bearer {token_b}"}).json()
    org_id_b = me_b["org_id"]

    return token_a, org_id_a, token_b, org_id_b


@pytest.fixture
def raw_client(client: TestClient) -> TestClient:  # type: ignore[return]
    """Remove the get_current_user override so auth is fully exercised."""
    app.dependency_overrides.pop(get_current_user, None)
    try:
        yield client  # type: ignore[misc]
    finally:
        pass


# ---------------------------------------------------------------------------
# Org isolation — list invoices
# ---------------------------------------------------------------------------


def test_user_only_sees_own_org_invoices(raw_client: TestClient, db: Session) -> None:
    token_a, org_id_a, token_b, org_id_b = _make_two_orgs(raw_client, db)

    # Seed an invoice for org A directly
    if db.get(Organization, org_id_a) is None:
        db.add(Organization(id=org_id_a, name="OrgA"))
        db.flush()
    inv_a = Invoice(
        id="inv-org-a-001",
        invoice_number="A-001",
        status="received",
        vendor="Vendor A",
        amount=Decimal("100.00"),
        org_id=org_id_a,
    )
    db.add(inv_a)
    db.commit()

    # User A can see their invoice
    resp_a = raw_client.get(_INVOICES_URL, headers={"Authorization": f"Bearer {token_a}"})
    assert resp_a.status_code == 200
    ids_a = [i["id"] for i in resp_a.json()]
    assert "inv-org-a-001" in ids_a

    # User B sees empty list (not org A's invoice)
    resp_b = raw_client.get(_INVOICES_URL, headers={"Authorization": f"Bearer {token_b}"})
    assert resp_b.status_code == 200
    ids_b = [i["id"] for i in resp_b.json()]
    assert "inv-org-a-001" not in ids_b


def test_user_gets_404_for_other_org_invoice(raw_client: TestClient, db: Session) -> None:
    token_a, org_id_a, token_b, org_id_b = _make_two_orgs(raw_client, db)

    # Ensure org row exists
    if db.get(Organization, org_id_a) is None:
        db.add(Organization(id=org_id_a, name="OrgA"))
        db.flush()

    inv_a = Invoice(
        id="inv-isolation-001",
        invoice_number="ISO-001",
        status="received",
        vendor="Vendor A",
        amount=Decimal("200.00"),
        org_id=org_id_a,
    )
    db.add(inv_a)
    db.commit()

    # User B tries to fetch org A's invoice by id → 404
    resp = raw_client.get(
        f"{_INVOICES_URL}/inv-isolation-001",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp.status_code == 404


def test_user_cannot_comment_on_other_org_invoice(raw_client: TestClient, db: Session) -> None:
    token_a, org_id_a, token_b, org_id_b = _make_two_orgs(raw_client, db)

    if db.get(Organization, org_id_a) is None:
        db.add(Organization(id=org_id_a, name="OrgA"))
        db.flush()

    inv_a = Invoice(
        id="inv-comment-001",
        invoice_number="CMT-001",
        status="received",
        vendor="Vendor A",
        amount=Decimal("300.00"),
        org_id=org_id_a,
    )
    db.add(inv_a)
    db.commit()

    # User B tries to comment on org A's invoice → 404
    resp = raw_client.post(
        f"{_INVOICES_URL}/inv-comment-001/comments",
        json={"body": "sneaky comment"},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Founder signup → seeded org
# ---------------------------------------------------------------------------


def test_founder_signup_creates_org_with_invoices(raw_client: TestClient, db: Session) -> None:
    """When a founder signs up, the org is seeded with demo invoices."""
    raw_client.post(
        _SIGNUP_URL,
        json={"email": "founder@newco.com", "password": "pass1234", "org_name": "NewCo"},
    )
    resp = raw_client.post(_LOGIN_URL, json={"email": "founder@newco.com", "password": "pass1234"})
    token = resp.json()["access_token"]

    inv_resp = raw_client.get(_INVOICES_URL, headers={"Authorization": f"Bearer {token}"})
    assert inv_resp.status_code == 200
    # The seed produces at least some invoices
    assert len(inv_resp.json()) > 0


# ---------------------------------------------------------------------------
# Second signup to same org → pending
# ---------------------------------------------------------------------------


def test_second_signup_same_org_is_pending(raw_client: TestClient) -> None:
    raw_client.post(
        _SIGNUP_URL,
        json={"email": "founder@pendco.com", "password": "pass", "org_name": "PendCo"},
    )
    r2 = raw_client.post(
        _SIGNUP_URL,
        json={"email": "member@pendco.com", "password": "pass", "org_name": "PendCo"},
    )
    assert r2.status_code == 201
    assert r2.json()["status"] == "pending"


def test_pending_member_cannot_login(raw_client: TestClient) -> None:
    raw_client.post(
        _SIGNUP_URL,
        json={"email": "founder@loginco.com", "password": "pass", "org_name": "LoginCo"},
    )
    raw_client.post(
        _SIGNUP_URL,
        json={"email": "pending@loginco.com", "password": "pass", "org_name": "LoginCo"},
    )
    resp = raw_client.post(_LOGIN_URL, json={"email": "pending@loginco.com", "password": "pass"})
    assert resp.status_code == 403
    assert "pending" in resp.json()["detail"].lower()
