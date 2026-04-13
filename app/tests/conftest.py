"""Shared pytest fixtures."""
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app

TEST_API_KEY = "test-key"


@pytest.fixture(scope="session")
def client():
    settings.API_KEY = TEST_API_KEY
    with TestClient(app, headers={"X-API-Key": TEST_API_KEY}) as c:
        yield c
