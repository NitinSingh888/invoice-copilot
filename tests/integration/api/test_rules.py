from __future__ import annotations

from collections.abc import Generator
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import Session, sessionmaker

import app.db.models  # noqa: F401 — populate metadata
from app.api.deps import get_db
from app.db.base import Base
from app.db.models.correction import Correction
from app.main import app


# ---------------------------------------------------------------------------
# Per-test in-memory DB (StaticPool so all connections share the same db)
# ---------------------------------------------------------------------------


def _make_client(seed_corrections: bool) -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, expire_on_commit=False)

    if seed_corrections:
        with TestingSession() as s:
            for i, over_pct in enumerate(["0.06", "0.04", "0.07"]):
                s.add(
                    Correction(
                        id=f"corr-seed-{i}",
                        invoice_id=f"inv-seed-{i}",
                        vendor="Acme Corp",
                        finding_code="OVER_TOLERANCE",
                        user_action="route",
                        over_pct=Decimal(over_pct),
                    )
                )
            s.commit()

    def override_get_db() -> Generator[Session, None, None]:
        s: Session = TestingSession()
        try:
            yield s
            s.commit()
        finally:
            s.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c

    app.dependency_overrides.pop(get_db, None)
    engine.dispose()


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    yield from _make_client(seed_corrections=True)


@pytest.fixture()
def client_empty() -> Generator[TestClient, None, None]:
    yield from _make_client(seed_corrections=False)


# ---------------------------------------------------------------------------
# POST /rules/propose — with corrections
# ---------------------------------------------------------------------------


def test_propose_rule_returns_proposal(client: TestClient) -> None:
    resp = client.post("/api/v1/rules/propose")
    assert resp.status_code == 200
    data = resp.json()
    assert Decimal(str(data["threshold_pct"])) == Decimal("0.08")
    assert data["route"] == "Priya"
    assert data["candidate"]["vendor"] == "Acme Corp"


# ---------------------------------------------------------------------------
# POST /rules/propose — no corrections → 204
# ---------------------------------------------------------------------------


def test_propose_rule_no_corrections_returns_204(client_empty: TestClient) -> None:
    resp = client_empty.post("/api/v1/rules/propose")
    assert resp.status_code == 204


# ---------------------------------------------------------------------------
# POST /rules/activate → 201
# ---------------------------------------------------------------------------


def test_activate_rule(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/rules/activate",
        json={"threshold_pct": "0.08", "route": "Priya"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "active"
    assert Decimal(str(data["max_over_pct"])) == Decimal("0.08")
    assert data["route"] == "Priya"


# ---------------------------------------------------------------------------
# GET /rules — lists active rule after activation
# ---------------------------------------------------------------------------


def test_list_rules_after_activate(client: TestClient) -> None:
    client.post(
        "/api/v1/rules/activate",
        json={"threshold_pct": "0.08", "route": "Priya"},
    )
    resp = client.get("/api/v1/rules")
    assert resp.status_code == 200
    rules = resp.json()
    assert len(rules) == 1
    assert rules[0]["status"] == "active"


# ---------------------------------------------------------------------------
# PATCH /rules/{id} — disable rule
# ---------------------------------------------------------------------------


def test_patch_rule_disable(client: TestClient) -> None:
    activate_resp = client.post(
        "/api/v1/rules/activate",
        json={"threshold_pct": "0.08", "route": "Priya"},
    )
    assert activate_resp.status_code == 201
    rule_id = activate_resp.json()["id"]

    resp = client.patch(f"/api/v1/rules/{rule_id}", json={"status": "disabled"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "disabled"


# ---------------------------------------------------------------------------
# PATCH /rules/{id} — missing rule → 404
# ---------------------------------------------------------------------------


def test_patch_rule_not_found(client: TestClient) -> None:
    resp = client.patch("/api/v1/rules/does-not-exist", json={"status": "disabled"})
    assert resp.status_code == 404
