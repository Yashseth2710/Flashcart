from collections.abc import Iterator
from typing import Any

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import Settings, get_settings

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    """Build the engine on first use so the app can start without a database."""
    global _engine
    if _engine is None:
        settings = get_settings()
        if not settings.database_configured:
            raise RuntimeError("DATABASE_URL is not set")
        _engine = create_engine(settings.database_url, **pool_for(settings))
    return _engine


def pool_for(settings: Settings) -> dict[str, Any]:
    """How to hold connections, which depends on what the app is running on.

    A long-running server pools them. Everyone reaching for the same item
    queues on one locked row and each waiting request holds a connection while
    it waits, so the pool has to be deep enough for the queue or people are
    turned away for want of a connection rather than for want of stock.

    Serverless is the opposite case and pooling there is actively harmful: each
    concurrent request gets a process of its own, so a pool is shared with
    nobody. It would hold connections open for a process about to be frozen,
    and multiply the count by however many instances happen to be awake — which
    is how a database runs out of connections while the app looks idle. Holding
    none and letting the database's own pooler do the pooling is the honest
    arrangement, and is why DATABASE_URL points at Neon's pooled endpoint.
    """
    if settings.serverless:
        # Pre-ping still earns its place: a resumed function can be holding a
        # connection the platform or the database has already let go.
        return {"poolclass": NullPool, "pool_pre_ping": True}

    return {
        # Neon closes idle connections when it scales to zero. Pre-ping catches
        # a dead one before it is handed out; recycling retires connections
        # before they get old enough to be dropped.
        "pool_pre_ping": True,
        "pool_recycle": 280,
        "pool_size": settings.pool_size,
        "max_overflow": settings.pool_overflow,
        # Better to be told the app is full than to sit behind a queue until
        # the database gives up on the transaction instead.
        "pool_timeout": settings.pool_wait_seconds,
    }


def get_session_factory() -> sessionmaker[Session]:
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)
    return _session_factory


def get_db() -> Iterator[Session]:
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()
