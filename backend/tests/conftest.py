"""Shared test fixtures — everything runs against a real Postgres database.

Tests use a dedicated `copilot_test` database (auto-created if missing) on the
same Postgres the app uses. Isolation is by TRUNCATE before every test, so each
test starts from an empty schema. No SQLite anywhere.

Requires a running Postgres (locally: `docker compose up -d postgres`). The URL
is taken from IC_TEST_DATABASE_URL, defaulting to the docker-compose Postgres.
"""

from __future__ import annotations

import os
from collections.abc import Generator, Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

import app.db.models  # noqa: F401 — populate Base.metadata
from app.api.deps import get_current_user, get_db, get_llm
from app.clients.llm.mock_client import MockClient
from app.db.base import Base
from app.db.models.organization import Organization
from app.db.models.user import User
from app.main import app

TEST_DATABASE_URL = os.environ.get(
    "IC_TEST_DATABASE_URL",
    "postgresql+psycopg://copilot:copilot@localhost:5432/copilot_test",
)

# The test org / user used by the client fixture
TEST_ORG_ID = "org-test0001"
TEST_ORG_NAME = "Test Org"
TEST_USER_ID = "usr-test0001"
TEST_USER_EMAIL = "test@example.com"


def _ensure_test_database() -> None:
    """Create the test database if it doesn't exist (connect via the default db)."""
    base, dbname = TEST_DATABASE_URL.rsplit("/", 1)
    dbname = dbname.split("?")[0]
    admin = create_engine(f"{base}/copilot", isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": dbname}
            ).scalar()
            if not exists:
                conn.execute(text(f'CREATE DATABASE "{dbname}"'))
    finally:
        admin.dispose()


@pytest.fixture(scope="session")
def _engine() -> Iterator[Engine]:
    _ensure_test_database()
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture(autouse=True)
def _clean(_engine: Engine) -> Iterator[None]:
    """Truncate every table before each test for full isolation."""
    tables = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
    if tables:
        with _engine.begin() as conn:
            conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    yield


@pytest.fixture
def db(_engine: Engine) -> Iterator[Session]:
    """A plain Session for unit tests and seeding. Commit to make writes visible
    to the API client (which uses separate connections to the same database)."""
    with Session(_engine, expire_on_commit=False) as session:
        yield session


@pytest.fixture
def client(_engine: Engine) -> Generator[TestClient, None, None]:
    """A TestClient whose get_db dependency uses the test database.

    Each request gets its own session (committed on success), so the app behaves
    exactly as in production. Created WITHOUT the lifespan context manager so the
    seed-on-boot hook does not run — tests seed explicitly.

    get_current_user is overridden with a pre-verified test user (with org_id)
    so that all existing tests continue to work without sending a Bearer token.
    Tests that exercise the auth flow directly should NOT rely on this override
    (they use the real dependency via a plain TestClient or override it themselves).
    """
    TestingSession = sessionmaker(bind=_engine, expire_on_commit=False)

    def override_get_db() -> Generator[Session, None, None]:
        session: Session = TestingSession()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # A synthetic verified user with org_id injected into every protected request.
    _test_user = User(
        id=TEST_USER_ID,
        email=TEST_USER_EMAIL,
        password_hash="",
        is_verified=True,
        verification_token=None,
        org_id=TEST_ORG_ID,
        role="admin",
    )

    app.dependency_overrides[get_db] = override_get_db
    # Force the deterministic mock LLM so tests never hit a real provider,
    # regardless of any IC_LLM_PROVIDER / API keys in a developer's .env.
    app.dependency_overrides[get_llm] = lambda: MockClient()
    app.dependency_overrides[get_current_user] = lambda: _test_user

    # Ensure the test Organization row exists so FK constraints on org_id pass
    # for any test that inserts entities directly with org_id=TEST_ORG_ID.
    with Session(_engine, expire_on_commit=False) as _setup_session:
        if _setup_session.get(Organization, TEST_ORG_ID) is None:
            _setup_session.add(Organization(id=TEST_ORG_ID, name=TEST_ORG_NAME))
            _setup_session.commit()

    test_client = TestClient(app)
    try:
        yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_llm, None)
        app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def seeded_client(client: TestClient, db: Session) -> TestClient:
    """A TestClient with the standard 'clearable' fixtures seeded (approved
    vendor + PO + cold-start history) and committed."""
    from tests.integration.api._seed import seed_clearable

    # Ensure the test org row exists so FK constraints pass
    if db.get(Organization, TEST_ORG_ID) is None:
        db.add(Organization(id=TEST_ORG_ID, name=TEST_ORG_NAME))
        db.flush()

    seed_clearable(db)
    db.commit()
    return client
