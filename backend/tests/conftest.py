from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.main import app
from app.models import *  # noqa: F403  (import side effect: registers tables)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(scope="session")
def engine():
    """Tests run against a real Postgres schema, since the guarantees under test
    are database constraints rather than application logic."""
    settings = get_settings()
    if not settings.database_configured:
        pytest.skip("DATABASE_URL is not set")
    return create_engine(settings.alembic_url)


@pytest.fixture
def db(engine) -> Iterator[Session]:
    """A session whose work is rolled back, so tests never leave rows behind.

    Work happens inside a savepoint: a constraint violation aborts that savepoint
    without poisoning the outer transaction, which is what lets a test provoke an
    IntegrityError and still clean up.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = sessionmaker(
        bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
    )()
    try:
        yield session
    finally:
        session.close()
        if transaction.is_active:
            transaction.rollback()
        connection.close()
