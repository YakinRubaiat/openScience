"""Tests for agent registry endpoints."""


def test_list_agents(client, auth_headers):
    response = client.get("/api/v1/agents", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 1
    assert body["total"] == len(body["agents"])
    agent = body["agents"][0]
    for field in (
        "name",
        "category",
        "description",
        "required_skills",
        "input_types",
        "output_types",
    ):
        assert field in agent


def test_get_agent_detail(client, auth_headers):
    agents = client.get("/api/v1/agents", headers=auth_headers).json()["agents"]
    name = agents[0]["name"]
    response = client.get(f"/api/v1/agents/{name}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["name"] == name


def test_get_unknown_agent_returns_404(client, auth_headers):
    response = client.get("/api/v1/agents/does_not_exist", headers=auth_headers)
    assert response.status_code == 404


def test_agents_require_authentication(client):
    assert client.get("/api/v1/agents").status_code in (401, 403)
    assert client.get("/api/v1/agents/qc_analyzer").status_code in (401, 403)
