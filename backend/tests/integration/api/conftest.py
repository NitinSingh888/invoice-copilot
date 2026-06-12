"""Shared fixtures for integration/api tests."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models.organization import Organization
from app.seed import seed_org

# Import the test org id from conftest
from tests.conftest import TEST_ORG_ID


@pytest.fixture
def demo_seeded_client(client: TestClient, db: Session) -> TestClient:
    """Client with the full demo seed loaded (real invoice PDFs).

    The seed is placed in TEST_ORG_ID so that the test user (who belongs to
    TEST_ORG_ID) can see it.
    """
    # Ensure the test org row exists
    if db.get(Organization, TEST_ORG_ID) is None:
        db.add(Organization(id=TEST_ORG_ID, name="Test Org"))
        db.flush()

    seed_org(db, TEST_ORG_ID)
    db.commit()
    return client
