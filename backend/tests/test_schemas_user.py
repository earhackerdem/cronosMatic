"""Tests for user-related Pydantic schemas."""
from datetime import datetime

import pytest
from pydantic import ValidationError

from app.schemas.user import (
    AuthResponse,
    AuthStatusResponse,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)


# ─── RegisterRequest ──────────────────────────────────────────────────────────

def test_register_request_valid():
    data = RegisterRequest(
        name="Alice",
        email="alice@example.com",
        password="password123",
        password_confirmation="password123",
    )
    assert data.name == "Alice"
    assert data.email == "alice@example.com"


def test_register_request_password_mismatch_raises():
    with pytest.raises(ValidationError) as exc_info:
        RegisterRequest(
            name="Alice",
            email="alice@example.com",
            password="password123",
            password_confirmation="different",
        )
    errors = exc_info.value.errors()
    assert any("password" in str(e).lower() for e in errors)


def test_register_request_password_too_short_raises():
    with pytest.raises(ValidationError):
        RegisterRequest(
            name="Alice",
            email="alice@example.com",
            password="short",
            password_confirmation="short",
        )


def test_register_request_invalid_email_raises():
    with pytest.raises(ValidationError):
        RegisterRequest(
            name="Alice",
            email="not-an-email",
            password="password123",
            password_confirmation="password123",
        )


# ─── LoginRequest ─────────────────────────────────────────────────────────────

def test_login_request_valid():
    data = LoginRequest(email="bob@example.com", password="anypass")
    assert data.email == "bob@example.com"
    assert data.password == "anypass"


def test_login_request_invalid_email_raises():
    with pytest.raises(ValidationError):
        LoginRequest(email="not-email", password="pass")


# ─── RefreshRequest ───────────────────────────────────────────────────────────

def test_refresh_request_valid():
    data = RefreshRequest(refresh_token="some.jwt.token")
    assert data.refresh_token == "some.jwt.token"


# ─── UserResponse ─────────────────────────────────────────────────────────────

def test_user_response_from_attributes():
    now = datetime.now()

    class FakeUser:
        id = 1
        name = "Dave"
        email = "dave@example.com"
        is_admin = False
        created_at = now
        updated_at = now

    user_resp = UserResponse.model_validate(FakeUser())
    assert user_resp.id == 1
    assert user_resp.name == "Dave"
    assert user_resp.email == "dave@example.com"


# ─── AuthResponse ─────────────────────────────────────────────────────────────

def test_auth_response_token_type_default():
    now = datetime.now()
    user_resp = UserResponse(
        id=1, name="Eve", email="eve@example.com",
        is_admin=False, created_at=now, updated_at=now
    )
    auth_resp = AuthResponse(
        user=user_resp,
        access_token="access",
        refresh_token="refresh",
    )
    assert auth_resp.token_type == "bearer"


# ─── TokenResponse ────────────────────────────────────────────────────────────

def test_token_response_has_token_type():
    resp = TokenResponse(access_token="tok")
    assert resp.token_type == "bearer"


# ─── AuthStatusResponse ───────────────────────────────────────────────────────

def test_auth_status_response_valid():
    now = datetime.now()
    user_resp = UserResponse(
        id=1, name="Eve", email="eve@example.com",
        is_admin=False, created_at=now, updated_at=now
    )
    status_resp = AuthStatusResponse(
        status="authenticated",
        message="User is logged in",
        user=user_resp,
        timestamp=now,
    )
    assert status_resp.status == "authenticated"
