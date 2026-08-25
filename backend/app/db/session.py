from collections.abc import Iterator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    """Build the engine on first use so the app can start without a database."""
    global _engine
    if _engine is None:
        settings = get_settings()
        if not settings.database_configured:
            raise RuntimeError("DATABASE_URL is not set")
        _engine = create_engine(
            settings.database_url,
            # Neon closes idle connections when it scales to zero. Pre-ping
            # catches a dead one before it is handed out; recycling retires
            # connections before they get old enough to be dropped.
            pool_pre_ping=True,
            pool_recycle=280,
            # A flash sale is the one moment everybody arrives together, and
            # they all queue on the same locked row: each waiting request is
            # holding a connection while it waits. The default pool of five
            # runs out long before the queue does.
            pool_size=settings.pool_size,
            max_overflow=settings.pool_overflow,
            # Better to be told the app is full than to sit behind a queue
            # until the database gives up on the transaction instead.
            pool_timeout=settings.pool_wait_seconds,
        )
    return _engine


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
