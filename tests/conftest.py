"""Shared pytest fixtures.

Why a fixture instead of a module-level TestClient(app):
FastAPI's lifespan (which opens the connection pool) only runs when
TestClient is used as a CONTEXT MANAGER. Writing `client = TestClient(app)`
at module level skips it entirely and every DB call fails with
"the pool is not open yet". This bites almost everyone once.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c
