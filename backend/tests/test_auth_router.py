"""Integration tests for auth and user routers."""

import pytest
from fastapi import Depends
from fastapi.routing import APIRoute

from app.api.deps import get_current_user_optional, require_admin
from app.domain.user.entity import User
from app.main import app


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
    assert data["status"] == "ok"
    assert data["message"] == "Authentication is working"
    assert "user" in data
    assert "timestamp" in data


async def test_auth_status_without_token_returns_401(auth_client):
    resp = await auth_client.get("/api/v1/auth-status")
    assert resp.status_code == 401


# ─── require_admin ────────────────────────────────────────────────────────────


@pytest.fixture(scope="module", autouse=True)
def _register_test_routes():
    """Register temporary test-only routes on the app for coverage testing."""
    from fastapi import APIRouter

    test_router = APIRouter()

    @test_router.get("/api/v1/test-admin-only")
    async def _admin_only(admin: User = Depends(require_admin)):
        return {"ok": True}

    @test_router.get("/api/v1/test-optional-auth")
    async def _optional_auth(user: User | None = Depends(get_current_user_optional)):
        return {"authenticated": user is not None}

    app.include_router(test_router)
    yield
    # Remove the test routes after the module finishes
    test_paths = {"/api/v1/test-admin-only", "/api/v1/test-optional-auth"}
    app.router.routes[:] = [
        r
        for r in app.router.routes
        if not (isinstance(r, APIRoute) and r.path in test_paths)
    ]


async def test_admin_endpoint_returns_403_for_non_admin(auth_client, registered_user):
    """Non-admin user should get 403 on admin-only endpoints."""
    access_token = registered_user["access_token"]
    resp = await auth_client.get(
        "/api/v1/test-admin-only",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Forbidden. User is not an administrator."


# ─── deps.py coverage ─────────────────────────────────────────────────────────


async def test_get_current_user_optional_without_token(auth_client):
    """get_current_user_optional returns None (not 401) when no token is provided."""
    resp = await auth_client.get("/api/v1/test-optional-auth")
    assert resp.status_code == 200
    assert resp.json()["authenticated"] is False


async def test_malformed_authorization_header_returns_401(auth_client, registered_user):
    """A header that doesn't start with 'Bearer ' should return 401."""
    resp = await auth_client.get(
        "/api/v1/users/me",
        headers={"Authorization": "Token notbearer"},
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid authorization header."


async def test_user_not_found_with_valid_jwt_returns_401(auth_client):
    """A token signed correctly but pointing to a non-existent user returns 401."""
    from datetime import datetime, timedelta, timezone

    from jose import jwt

    from app.config import settings

    # Build a valid access token for a user_id that doesn't exist in the test DB
    payload = {
        "sub": "99999",
        "email": "ghost@example.com",
        "is_admin": False,
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm="HS256")

    resp = await auth_client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "User not found."
