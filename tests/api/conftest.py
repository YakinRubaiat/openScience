"""Shared fixtures for API tests."""

import os
import sys
from pathlib import Path

# SQLAlchemy 2.1.x ships Cython extensions that can break on some Python
# builds ('InternalTraversal' object is not callable); disable them.
os.environ.setdefault("DISABLE_SQLALCHEMY_CEXT", "1")

import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# Use a per-session temporary SQLite database before any app import.
TEST_DB = PROJECT_ROOT / ".test-api.db"
if TEST_DB.exists():
    TEST_DB.unlink()
os.environ["OPENSCIENCE_API_DATABASE_URL"] = f"sqlite:///{TEST_DB}"
os.environ["OPENSCIENCE_API_SECRET_KEY"] = "test-secret-key"
os.environ["OPENSCIENCE_API_RATE_LIMIT_ENABLED"] = "false"

from openscience.api.database import reset_engine
from openscience.api.main import create_app


@pytest.fixture()
def app():
    # Reset state so every test gets a clean database and settings.
    if TEST_DB.exists():
        TEST_DB.unlink()
    reset_engine()
    application = create_app()
    yield application
    reset_engine()
    if TEST_DB.exists():
        TEST_DB.unlink()


@pytest.fixture()
def client(app):
    # ``with`` ensures startup/shutdown handlers run.
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def auth_headers(client):
    """Register a user (if needed) and return Authorization headers."""
    username = "testuser"
    password = "testpass123"
    client.post(
        "/api/v1/auth/register",
        json={"username": username, "email": "testuser@example.com", "password": password},
    )
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def second_auth_headers(client):
    username = "otheruser"
    password = "otherpass123"
    client.post(
        "/api/v1/auth/register",
        json={"username": username, "email": "otheruser@example.com", "password": password},
    )
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
