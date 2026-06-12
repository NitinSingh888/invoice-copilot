"""Shared fixtures for integration/api tests."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.seed import seed


@pytest.fixture
def demo_seeded_client(client: TestClient, db: Session) -> TestClient:
    """Client with the full demo seed loaded (real invoice PDFs)."""
    seed(db)
    db.commit()
    return client
