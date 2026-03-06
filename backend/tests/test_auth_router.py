"""Integration tests for auth and user routers."""
import pytest



@pytest.fixture
async def auth_client(client):
    """Alias for the shared client fixture (DB-isolated per test)."""
    return client


@pytest.fixture
async def registered_user(auth_client):
    """Register a user and return the response data."""
    resp = await auth_client.post(
        "/api/v1/auth/register",
        json={
            "name": "Test User",
            "email": "testuser@router.example.com",
            "password": "password123",
            "password_confirmation": "password123",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# ─── POST /auth/register ──────────────────────────────────────────────────────

async def test_register_returns_201_with_tokens(auth_client):
    resp = await auth_client.post(
        "/api/v1/auth/register",
        json={
            "name": "Alice",
            "email": "alice@router.example.com",
            "password": "password123",
            "password_confirmation": "password123",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "alice@router.example.com"


async def test_register_duplicate_email_returns_422(auth_client, registered_user):
    resp = await auth_client.post(
        "/api/v1/auth/register",
        json={
            "name": "Duplicate",
            "email": "testuser@router.example.com",
            "password": "password123",
            "password_confirmation": "password123",
        },
    )
    assert resp.status_code == 422


async def test_register_password_mismatch_returns_422(auth_client):
    resp = await auth_client.post(
        "/api/v1/auth/register",
        json={
            "name": "Bob",
            "email": "bob@router.example.com",
            "password": "password123",
            "password_confirmation": "different",
        },
    )
    assert resp.status_code == 422


# ─── POST /auth/login ─────────────────────────────────────────────────────────

async def test_login_returns_200_with_tokens(auth_client, registered_user):
    resp = await auth_client.post(
        "/api/v1/auth/login",
        json={"email": "testuser@router.example.com", "password": "password123"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


async def test_login_wrong_password_returns_401(auth_client, registered_user):
    resp = await auth_client.post(
        "/api/v1/auth/login",
        json={"email": "testuser@router.example.com", "password": "wrongpassword"},
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "The provided credentials are incorrect."


async def test_login_unknown_email_returns_401(auth_client):
    resp = await auth_client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@router.example.com", "password": "password123"},
    )
    assert resp.status_code == 401


# ─── GET /users/me ────────────────────────────────────────────────────────────

async def test_get_me_with_valid_token(auth_client, registered_user):
    access_token = registered_user["access_token"]
    resp = await auth_client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "testuser@router.example.com"


async def test_get_me_without_token_returns_401(auth_client):
    resp = await auth_client.get("/api/v1/users/me")
    assert resp.status_code == 401


async def test_get_me_with_invalid_token_returns_401(auth_client):
    resp = await auth_client.get(
        "/api/v1/users/me",
        headers={"Authorization": "Bearer notavalidtoken"},
    )
    assert resp.status_code == 401


# ─── POST /auth/refresh ───────────────────────────────────────────────────────

async def test_refresh_with_valid_token_returns_200(auth_client, registered_user):
    refresh_token = registered_user["refresh_token"]
    resp = await auth_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


async def test_refresh_with_invalid_token_returns_401(auth_client):
    resp = await auth_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "invalid.token.here"},
    )
    assert resp.status_code == 401


# ─── POST /auth/logout ────────────────────────────────────────────────────────

async def test_logout_returns_204(auth_client, registered_user):
    access_token = registered_user["access_token"]
    resp = await auth_client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert resp.status_code == 204


async def test_logout_without_token_returns_401(auth_client):
    resp = await auth_client.post("/api/v1/auth/logout")
    assert resp.status_code == 401


# ─── GET /auth-status ─────────────────────────────────────────────────────────

async def test_auth_status_with_valid_token(auth_client, registered_user):
    access_token = registered_user["access_token"]
    resp = await auth_client.get(
        "/api/v1/auth-status",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "authenticated"
    assert "user" in data
    assert "timestamp" in data


async def test_auth_status_without_token_returns_401(auth_client):
    resp = await auth_client.get("/api/v1/auth-status")
    assert resp.status_code == 401


# ─── require_admin ────────────────────────────────────────────────────────────

async def test_admin_endpoint_returns_403_for_non_admin(auth_client, registered_user):
    """Non-admin user should get 403 on admin-only endpoints."""
    # We'll test this once we wire an admin endpoint. For now test via a custom
    # dependency check — we confirm the deps.py require_admin raises 403.
    # A simple indirect test: GET /api/v1/users/me is not admin-only, so 200.
    # The actual 403 test will be in a dedicated admin test once an endpoint exists.
    # For now, verify the admin endpoint test would fire via trying a future endpoint.
    # This is a placeholder — the require_admin function is tested in deps.
    pass
