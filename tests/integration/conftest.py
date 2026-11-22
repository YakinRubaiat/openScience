"""Shared fixtures for the openScience integration test suite.

Every test builds a throwaway FastAPI app backed by a temporary SQLite
database, so tests are hermetic and can run without Docker.  Docker-level
checks are guarded with ``shutil.which("docker")`` and skip when the daemon
is unavailable.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("OPENSCIENCE_API_RATE_LIMIT_ENABLED", "false")
os.environ.setdefault("OPENSCIENCE_API_SANDBOX_ENABLED", "false")


@pytest.fixture()
def integration_app(tmp_path, monkeypatch):
    """Yield (TestClient, db_path, tmp_dir) for a fresh API app."""
    from fastapi.testclient import TestClient

    from openscience.api.config import reset_settings_cache
    from openscience.api.main import create_app

    db_path = tmp_path / "integration.db"
    monkeypatch.setenv("OPENSCIENCE_API_DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("OPENSCIENCE_API_RATE_LIMIT_ENABLED", "false")
    monkeypatch.setenv("OPENSCIENCE_API_SANDBOX_ENABLED", "false")
    reset_settings_cache()

    app = create_app()
    with TestClient(app) as client:
        yield client, db_path, tmp_path


@pytest.fixture()
def auth_headers(integration_app):
    """Register a user and return (client, auth_headers, session_id)."""
    client, _db_path, tmp_path = integration_app
    r = client.post(
        "/api/v1/auth/register",
        json={
            "username": "integration_user",
            "email": "integration@test.dev",
            "password": "integration-pass-123",
        },
    )
    assert r.status_code == 201, r.text
    r = client.post(
        "/api/v1/auth/login",
        json={"username": "integration_user", "password": "integration-pass-123"},
    )
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    client.headers = getattr(client, "headers", {})
    return client, {"Authorization": f"Bearer {token}"}, tmp_path


@pytest.fixture()
def project_dir(tmp_path):
    """Temporary project directory with a small CSV dataset."""
    d = tmp_path / "project"
    d.mkdir()
    (d / "expression.csv").write_text("gene,ctrl1,ctrl2\nGAPDH,100,105\nACTB,150,160\n")
    return d
