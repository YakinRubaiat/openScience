"""Tests for openscience server."""

import pytest

from openscience.server import create_app


@pytest.fixture
def app():
    """Create and configure a test app instance."""
    app = create_app()
    app.config["TESTING"] = True
    return app


@pytest.fixture
def client(app):
    """Create a test client."""
    return app.test_client()


def test_health_endpoint(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "healthy"
    assert data["service"] == "openscience-api"


def test_index_route(client):
    """Test index route."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"openScience" in response.data


def test_list_agents_endpoint(client):
    """Test agents listing endpoint."""
    response = client.get("/api/agents")
    assert response.status_code == 200
    data = response.get_json()
    assert "agents" in data
    assert isinstance(data["agents"], list)
