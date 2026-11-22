"""Tests for session lifecycle endpoints."""


def _create_session(client, headers, name="my-session"):
    response = client.post(
        "/api/v1/sessions",
        json={"name": name, "compute_backend": "local"},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_create_and_get_session(client, auth_headers):
    created = _create_session(client, auth_headers)
    assert created["name"] == "my-session"
    assert created["status"] == "active"

    fetched = client.get(f"/api/v1/sessions/{created['id']}", headers=auth_headers)
    assert fetched.status_code == 200
    assert fetched.json()["id"] == created["id"]


def test_session_lifecycle_full_flow(client, auth_headers):
    session = _create_session(client, auth_headers, name="flow")
    sid = session["id"]

    # Load data
    load = client.post(
        f"/api/v1/sessions/{sid}/load",
        json={"file_path": "data/experiment.csv", "format": "csv", "name": "experiment"},
        headers=auth_headers,
    )
    assert load.status_code == 200, load.text
    assert load.json()["task_type"] == "load"
    assert load.json()["status"] == "completed"

    # Run analysis
    analyze = client.post(
        f"/api/v1/sessions/{sid}/analyze",
        json={"task": "quality control of the data"},
        headers=auth_headers,
    )
    assert analyze.status_code == 200, analyze.text
    assert analyze.json()["task_type"] == "analyze"
    assert analyze.json()["status"] == "completed"
    assert analyze.json()["result"] is not None

    # Visualize (uses latest result)
    visualize = client.post(
        f"/api/v1/sessions/{sid}/visualize",
        json={"type": "umap", "style": "publication"},
        headers=auth_headers,
    )
    assert visualize.status_code == 200, visualize.text
    assert visualize.json()["task_type"] == "visualize"

    # Write up
    write = client.post(
        f"/api/v1/sessions/{sid}/write",
        json={"style": "nature", "citation_format": "apa"},
        headers=auth_headers,
    )
    assert write.status_code == 200, write.text
    assert write.json()["task_type"] == "write"

    # Results aggregate everything
    results = client.get(f"/api/v1/sessions/{sid}/results", headers=auth_headers)
    assert results.status_code == 200, results.text
    body = results.json()
    assert body["session_id"] == sid
    assert len(body["results"]) >= 1
    task_types = {t["task_type"] for t in body["tasks"]}
    assert {"load", "analyze", "visualize", "write"} <= task_types

    # Session now reports the loaded dataset key
    fetched = client.get(f"/api/v1/sessions/{sid}", headers=auth_headers)
    assert "experiment" in fetched.json()["data_keys"]

    # Delete
    deleted = client.delete(f"/api/v1/sessions/{sid}", headers=auth_headers)
    assert deleted.status_code == 200
    assert client.get(f"/api/v1/sessions/{sid}", headers=auth_headers).status_code == 404


def test_get_unknown_session_returns_404(client, auth_headers):
    assert client.get("/api/v1/sessions/nope", headers=auth_headers).status_code == 404


def test_session_ownership_enforced(client, auth_headers, second_auth_headers):
    session = _create_session(client, auth_headers, name="private")
    sid = session["id"]
    response = client.get(f"/api/v1/sessions/{sid}", headers=second_auth_headers)
    assert response.status_code == 403


def test_sessions_require_authentication(client):
    assert client.post("/api/v1/sessions", json={"name": "x"}).status_code in (401, 403)
    assert client.get("/api/v1/sessions/whatever").status_code in (401, 403)


def test_analysis_validation_error(client, auth_headers):
    session = _create_session(client, auth_headers, name="validate")
    sid = session["id"]
    response = client.post(f"/api/v1/sessions/{sid}/analyze", json={}, headers=auth_headers)
    assert response.status_code == 422


def test_visualize_without_results_returns_400(client, auth_headers):
    session = _create_session(client, auth_headers, name="noviz")
    sid = session["id"]
    response = client.post(f"/api/v1/sessions/{sid}/visualize", json={}, headers=auth_headers)
    assert response.status_code == 400


def test_path_traversal_rejected(client, auth_headers):
    session = _create_session(client, auth_headers, name="paths")
    sid = session["id"]
    response = client.post(
        f"/api/v1/sessions/{sid}/load",
        json={"file_path": "../../etc/passwd"},
        headers=auth_headers,
    )
    assert response.status_code == 422
