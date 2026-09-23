"""Database engine and request-scoped sessions.

Synchronous on purpose. An endpoint here does one short insert; everything
expensive happens on the Celery worker, which is not async either. An async
driver would add a second concurrency model for no gain.
"""

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    kwargs: dict = {"pool_pre_ping": True, "future": True}
    if settings.database_url.startswith("sqlite"):
        # Tests share one database across the TestClient's threads; the
        # default SQLite behaviour refuses a connection used off-thread.
        kwargs["connect_args"] = {"check_same_thread": False}
    return create_engine(settings.database_url, **kwargs)


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False, future=True)


def get_db() -> Iterator[Session]:
    """FastAPI dependency.

    Committing is the endpoint's decision, not this one's. Rolling back on an
    exception is the only safe default: a half-written receipt is worse than
    no receipt.
    """
    session = get_session_factory()()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
