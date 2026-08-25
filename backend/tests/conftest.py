from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401  (import side effect: registers tables)
from app.core.config import get_settings
from app.db.session import get_db
from app.main import app


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


@pytest.fixture
def client(db: Session) -> Iterator[TestClient]:
    """A client whose requests run in the test's transaction, so anything a
    request writes is rolled back with everything else."""
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# Concurrency tests need connections that commit, which the fixtures above
# deliberately prevent. Theirs live alongside rather than replacing these.
# The sweep is autouse, but only where pytest can see it: a fixture is not
# collected from a module that is merely imported, so it is named here too.
from tests.conftest_concurrency import (  # noqa: E402,F401
    committing_engine,
    sessions,
    sweep_abandoned_rows,
    world,
)
