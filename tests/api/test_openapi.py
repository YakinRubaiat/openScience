"""Tests for the OpenAPI documentation and health endpoints."""


def test_openapi_schema(client):
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "openScience API"
    for path in (
        "/api/v1/agents",
        "/api/v1/agents/{name}",
        "/api/v1/sessions",
        "/api/v1/sessions/{session_id}",
        "/api/v1/sessions/{session_id}/load",
        "/api/v1/sessions/{session_id}/analyze",
        "/api/v1/sessions/{session_id}/visualize",
        "/api/v1/sessions/{session_id}/write",
        "/api/v1/sessions/{session_id}/results",
        "/api/v1/auth/register",
        "/api/v1/auth/login",
    ):
        assert path in schema["paths"], f"missing path: {path}"


def test_swagger_docs(client):
    response = client.get("/docs")
    assert response.status_code == 200
    assert "swagger" in response.text.lower()


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
