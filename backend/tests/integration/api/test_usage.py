from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.clients.llm.metered import MeteredLLMClient
from app.clients.llm.mock_client import MockClient
from app.clients.llm.types import ChatMessage
from app.clients.llm.usage import entity_context
from app.db.models.llm_call import LlmCall
from app.db.models.organization import Organization
from app.db.models.user import User
from app.repositories import llm_call_repo
from tests.conftest import TEST_ORG_ID, TEST_ORG_NAME, TEST_USER_EMAIL, TEST_USER_ID


def _seed_user(db: Session) -> None:
    if db.get(Organization, TEST_ORG_ID) is None:
        db.add(Organization(id=TEST_ORG_ID, name=TEST_ORG_NAME))
        db.commit()
    if db.get(User, TEST_USER_ID) is None:
        db.add(
            User(
                id=TEST_USER_ID,
                email=TEST_USER_EMAIL,
                password_hash="",
                is_verified=True,
                verification_token=None,
                org_id=TEST_ORG_ID,
                role="admin",
            )
        )
        db.commit()


def test_usage_endpoint_totals_and_breakdowns(client: TestClient, db: Session) -> None:
    _seed_user(db)
    # Two extractions on anthropic + one mock conversation.
    llm_call_repo.add(
        db, id="llm-1", org_id=TEST_ORG_ID, user_id=TEST_USER_ID, purpose="extract_invoice",
        reason="r", provider="anthropic", model="claude-sonnet-4", input_tokens=1000,
        output_tokens=500, cost_usd=Decimal("0.010500"), latency_ms=10, status="ok",
    )
    llm_call_repo.add(
        db, id="llm-2", org_id=TEST_ORG_ID, user_id=TEST_USER_ID, purpose="extract_invoice",
        reason="r", provider="anthropic", model="claude-sonnet-4", input_tokens=2000,
        output_tokens=0, cost_usd=Decimal("0.006000"), latency_ms=12, status="ok",
    )
    llm_call_repo.add(
        db, id="llm-3", org_id=TEST_ORG_ID, user_id=TEST_USER_ID, purpose="converse",
        reason="r", provider="mock", model="mock", input_tokens=0, output_tokens=0,
        cost_usd=Decimal("0"), latency_ms=1, status="ok",
    )
    db.commit()

    resp = client.get("/api/v1/usage")
    assert resp.status_code == 200
    body = resp.json()

    assert body["currency"] == "USD"
    assert body["total_calls"] == 3
    assert Decimal(body["total_cost_usd"]) == Decimal("0.016500")
    assert body["total_input_tokens"] == 3000
    assert body["total_output_tokens"] == 500

    purposes = {p["purpose"]: p for p in body["by_purpose"]}
    assert purposes["extract_invoice"]["calls"] == 2
    assert Decimal(purposes["extract_invoice"]["cost_usd"]) == Decimal("0.016500")
    # Costliest purpose first
    assert body["by_purpose"][0]["purpose"] == "extract_invoice"

    assert len(body["recent"]) == 3
    assert body["recent"][0]["purpose"] in {"extract_invoice", "converse"}


def test_usage_is_scoped_to_the_org(client: TestClient, db: Session) -> None:
    _seed_user(db)
    db.add(Organization(id="org-someone-else", name="Other Co"))
    db.commit()
    llm_call_repo.add(
        db, id="llm-other", org_id="org-someone-else", user_id=None, purpose="converse",
        reason="r", provider="anthropic", model="claude-sonnet-4", input_tokens=5000,
        output_tokens=5000, cost_usd=Decimal("0.090000"), latency_ms=5, status="ok",
    )
    db.commit()

    body = client.get("/api/v1/usage").json()
    # The other org's spend must not leak into this team's totals.
    assert body["total_calls"] == 0
    assert Decimal(body["total_cost_usd"]) == Decimal("0")


def test_metered_client_records_a_call(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The metering wrapper logs each call with purpose, provider, and cost."""
    _seed_user(db)
    # Point the metering wrapper's own session at the test database.
    test_sessionmaker = sessionmaker(bind=db.get_bind(), expire_on_commit=False)
    monkeypatch.setattr("app.db.session.SessionLocal", test_sessionmaker)

    metered = MeteredLLMClient(MockClient(), org_id=TEST_ORG_ID, user_id=TEST_USER_ID)
    with entity_context("invoice", "inv-xyz"):
        reply = metered.converse(history=[ChatMessage(role="user", content="hi")], context={})
    assert reply.text  # delegation works

    rows = list(db.execute(select(LlmCall).where(LlmCall.org_id == TEST_ORG_ID)).scalars().all())
    assert len(rows) == 1
    row = rows[0]
    assert row.purpose == "converse"
    assert row.provider == "mock"
    assert row.cost_usd == Decimal("0")  # mock makes no real API call
    assert row.entity_type == "invoice" and row.entity_id == "inv-xyz"
    assert row.user_id == TEST_USER_ID
    assert row.status == "ok"
