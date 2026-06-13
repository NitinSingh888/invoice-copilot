from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_health() -> None:
    data = TestClient(app).get("/api/v1/health").json()
    assert data["status"] == "ok"
    assert "provider" in data
    assert "live" in data


def test_ready_ok_when_db_reachable() -> None:
    resp = TestClient(app).get("/api/v1/health/ready")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ready", "db": "ok"}
