"""Integration fixtures.

The engine reads its configuration once, through an lru_cache, so the
environment has to be set before anything under `app.` is imported. That is
why these assignments sit at module scope and not inside a fixture.
"""

import os
import tempfile

import pytest

_TMP = tempfile.mkdtemp(prefix="screening-tests-")
_SECRET = "test-secret-that-is-long-enough-0123"

os.environ["SCREENING_ENVIRONMENT"] = "test"
os.environ["SCREENING_DATABASE_URL"] = f"sqlite:///{_TMP}/ledger.db"
os.environ["SCREENING_QUARANTINE_ROOT"] = f"{_TMP}/quarantine"
# Length is enforced by the settings model; the value is meaningless here.
os.environ["SCREENING_CALLBACK_SECRET"] = _SECRET


@pytest.fixture(scope="session")
def secret() -> str:
    return _SECRET


@pytest.fixture(scope="session")
def quarantine_root() -> str:
    return os.environ["SCREENING_QUARANTINE_ROOT"]


@pytest.fixture(scope="session")
def client():
    from fastapi.testclient import TestClient

    from app.db.base import Base
    from app.db.session import get_engine
    from app.main import create_app

    # create_all rather than `alembic upgrade head`: the migration is already
    # checked against these same models by `alembic check`, so running it here
    # would test the same thing twice and make the suite need a migration
    # runner to execute at all.
    Base.metadata.create_all(get_engine())
    with TestClient(create_app()) as test_client:
        yield test_client
