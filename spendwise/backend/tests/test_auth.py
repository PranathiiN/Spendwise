def test_register_returns_token_and_user(client):
    resp = client.post(
        "/api/auth/register",
        json={"name": "Alice", "email": "  Alice@Example.COM ", "password": "Password123"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["access_token"]
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "alice@example.com"  # normalized
    assert data["user"]["preferred_currency"] == "INR"
    assert "password_hash" not in data["user"]


def test_register_duplicate_email_is_case_insensitive(client, register_user):
    register_user(email="alice@example.com")
    resp = client.post(
        "/api/auth/register",
        json={"name": "Other", "email": "ALICE@example.com", "password": "Password123"},
    )
    assert resp.status_code == 409


def test_register_rejects_weak_password(client):
    resp = client.post("/api/auth/register", json={"name": "A", "email": "a@example.com", "password": "short"})
    assert resp.status_code == 422
    resp = client.post(
        "/api/auth/register", json={"name": "A", "email": "a@example.com", "password": "onlyletters"}
    )
    assert resp.status_code == 422


def test_register_rejects_invalid_email(client):
    resp = client.post("/api/auth/register", json={"name": "A", "email": "not-an-email", "password": "Password123"})
    assert resp.status_code == 422


def test_login_success_and_case_insensitive_email(client, register_user):
    register_user(email="alice@example.com", password="Password123")
    resp = client.post("/api/auth/login", json={"email": "ALICE@example.com", "password": "Password123"})
    assert resp.status_code == 200
    assert resp.json()["access_token"]


def test_login_wrong_password(client, register_user):
    register_user(email="alice@example.com", password="Password123")
    resp = client.post("/api/auth/login", json={"email": "alice@example.com", "password": "Wrong12345"})
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Incorrect email or password"


def test_login_unknown_email_same_error(client):
    resp = client.post("/api/auth/login", json={"email": "nobody@example.com", "password": "Password123"})
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Incorrect email or password"


def test_me_requires_auth(client):
    assert client.get("/api/auth/me").status_code == 401


def test_me_rejects_invalid_token(client):
    resp = client.get("/api/auth/me", headers={"Authorization": "Bearer not.a.real.token"})
    assert resp.status_code == 401


def test_me_returns_current_user(client, auth_headers):
    resp = client.get("/api/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == "alice@example.com"


def test_update_profile(client, auth_headers):
    resp = client.patch("/api/auth/me", json={"name": "Alice B", "preferred_currency": "usd"}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "Alice B"
    assert resp.json()["preferred_currency"] == "USD"

    resp = client.patch("/api/auth/me", json={"preferred_currency": "XYZ"}, headers=auth_headers)
    assert resp.status_code == 422


def test_change_password(client, auth_headers):
    resp = client.post(
        "/api/auth/change-password",
        json={"current_password": "wrong", "new_password": "NewPassword1"},
        headers=auth_headers,
    )
    assert resp.status_code == 400

    resp = client.post(
        "/api/auth/change-password",
        json={"current_password": "Password123", "new_password": "NewPassword1"},
        headers=auth_headers,
    )
    assert resp.status_code == 204
    assert client.post("/api/auth/login", json={"email": "alice@example.com", "password": "NewPassword1"}).status_code == 200
    assert client.post("/api/auth/login", json={"email": "alice@example.com", "password": "Password123"}).status_code == 401
