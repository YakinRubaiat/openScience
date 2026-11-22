"""Tests for authentication endpoints."""


def _register(client, username="alice", email="alice@example.com", password="supersecret1"):
    return client.post(
        "/api/v1/auth/register",
        json={"username": username, "email": email, "password": password},
    )


def test_register_and_login(client):
    response = _register(client)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["username"] == "alice"
    assert body["email"] == "alice@example.com"
    assert "hashed_password" not in body

    login = client.post(
        "/api/v1/auth/login", json={"username": "alice", "password": "supersecret1"}
    )
    assert login.status_code == 200
    token = login.json()
    assert token["token_type"] == "bearer"
    assert token["access_token"]

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token['access_token']}"})
    assert me.status_code == 200
    assert me.json()["username"] == "alice"


def test_duplicate_registration_rejected(client):
    assert _register(client).status_code == 201
    assert _register(client).status_code == 409


def test_login_wrong_password(client):
    assert _register(client).status_code == 201
    login = client.post("/api/v1/auth/login", json={"username": "alice", "password": "wrong"})
    assert login.status_code == 401


def test_login_unknown_user(client):
    login = client.post("/api/v1/auth/login", json={"username": "ghost", "password": "nope1234"})
    assert login.status_code == 401


def test_register_weak_password_rejected(client):
    response = _register(client, password="short")
    assert response.status_code == 422


def test_protected_endpoint_requires_token(client):
    assert client.get("/api/v1/agents").status_code in (401, 403)


def test_invalid_token_rejected(client):
    response = client.get("/api/v1/agents", headers={"Authorization": "Bearer not-a-token"})
    assert response.status_code == 401
