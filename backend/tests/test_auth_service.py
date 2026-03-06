"""Tests for AuthService with mocked repositories."""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest

from app.config import settings
from app.domain.refresh_token.entity import RefreshToken
from app.domain.user.entity import User
from app.services.auth import (
    AuthService,
    InvalidCredentialsError,
    InvalidTokenError,
    UserConflictError,
)


def make_auth_service(user_repo=None, refresh_token_repo=None):
    if user_repo is None:
        user_repo = AsyncMock()
    if refresh_token_repo is None:
        refresh_token_repo = AsyncMock()
    return AuthService(user_repo, refresh_token_repo, settings)


# ─── Password hashing ─────────────────────────────────────────────────────────

def test_hash_password_returns_string():
    service = make_auth_service()
    hashed = service.hash_password("mysecret")
    assert isinstance(hashed, str)
    assert hashed != "mysecret"


def test_verify_password_correct():
    service = make_auth_service()
    hashed = service.hash_password("mysecret")
    assert service.verify_password("mysecret", hashed) is True


def test_verify_password_wrong():
    service = make_auth_service()
    hashed = service.hash_password("mysecret")
    assert service.verify_password("wrongpass", hashed) is False


# ─── Token creation ────────────────────────────────────────────────────────────

def test_create_access_token_returns_str():
    service = make_auth_service()
    user = User(id=1, name="Alice", email="alice@test.com", hashed_password="x")
    token = service.create_access_token(user)
    assert isinstance(token, str)


def test_create_access_token_contains_user_info():
    from jose import jwt
    service = make_auth_service()
    user = User(id=7, name="Bob", email="bob@test.com", hashed_password="x", is_admin=True)
    token = service.create_access_token(user)
    payload = jwt.decode(token, settings.jwt_secret_key, algorithms=["HS256"])
    # sub is stored as string in JWT (python-jose requirement), converted to int by decode_access_token
    assert int(payload["sub"]) == 7
    assert payload["email"] == "bob@test.com"
    assert payload["is_admin"] is True
    assert payload["type"] == "access"


def test_create_refresh_token_returns_tuple():
    service = make_auth_service()
    user = User(id=1, name="Alice", email="alice@test.com", hashed_password="x")
    token_str, jti = service.create_refresh_token(user)
    assert isinstance(token_str, str)
    assert isinstance(jti, str)
    assert len(jti) > 0


def test_create_refresh_token_contains_type_and_jti():
    from jose import jwt
    service = make_auth_service()
    user = User(id=3, name="Carol", email="carol@test.com", hashed_password="x")
    token_str, jti = service.create_refresh_token(user)
    payload = jwt.decode(token_str, settings.jwt_secret_key, algorithms=["HS256"])
    assert payload["type"] == "refresh"
    assert payload["jti"] == jti
    # sub is stored as string in JWT (python-jose requirement)
    assert int(payload["sub"]) == 3


# ─── decode_access_token ───────────────────────────────────────────────────────

def test_decode_access_token_valid():
    service = make_auth_service()
    user = User(id=5, name="Dave", email="dave@test.com", hashed_password="x")
    token = service.create_access_token(user)
    payload = service.decode_access_token(token)
    assert payload["sub"] == 5
    assert payload["type"] == "access"


def test_decode_access_token_invalid_raises():
    service = make_auth_service()
    with pytest.raises(InvalidTokenError):
        service.decode_access_token("not.a.valid.token")


def test_decode_access_token_wrong_type_raises():
    """A refresh token must not be accepted by decode_access_token."""
    service = make_auth_service()
    user = User(id=5, name="Dave", email="dave@test.com", hashed_password="x")
    refresh_token_str, _ = service.create_refresh_token(user)
    with pytest.raises(InvalidTokenError):
        service.decode_access_token(refresh_token_str)


# ─── register ─────────────────────────────────────────────────────────────────

async def test_register_creates_user_and_returns_tokens():
    user_repo = AsyncMock()
    rt_repo = AsyncMock()

    user_repo.get_by_email.return_value = None
    created_user = User(id=1, name="Alice", email="alice@test.com", hashed_password="hashed")
    user_repo.create.return_value = created_user

    expires = datetime.now(timezone.utc) + timedelta(days=7)
    rt_repo.create.return_value = RefreshToken(
        id=1, user_id=1, token_jti="jti", expires_at=expires
    )

    service = make_auth_service(user_repo, rt_repo)
    user, access_token, refresh_token = await service.register(
        name="Alice", email="alice@test.com", password="password123"
    )

    assert user.id == 1
    assert isinstance(access_token, str)
    assert isinstance(refresh_token, str)
    user_repo.get_by_email.assert_awaited_once_with("alice@test.com")
    user_repo.create.assert_awaited_once()


async def test_register_duplicate_email_raises_conflict():
    user_repo = AsyncMock()
    user_repo.get_by_email.return_value = User(
        id=1, name="Existing", email="dup@test.com", hashed_password="x"
    )

    service = make_auth_service(user_repo)
    with pytest.raises(UserConflictError):
        await service.register(name="New", email="dup@test.com", password="password123")


# ─── login ────────────────────────────────────────────────────────────────────

async def test_login_returns_tokens():
    service_temp = make_auth_service()
    hashed = service_temp.hash_password("correct_pass")

    user_repo = AsyncMock()
    rt_repo = AsyncMock()

    user = User(id=2, name="Bob", email="bob@test.com", hashed_password=hashed)
    user_repo.get_by_email.return_value = user
    rt_repo.revoke_by_user_id.return_value = None

    expires = datetime.now(timezone.utc) + timedelta(days=7)
    rt_repo.create.return_value = RefreshToken(
        id=1, user_id=2, token_jti="jti2", expires_at=expires
    )

    service = make_auth_service(user_repo, rt_repo)
    returned_user, access_token, refresh_token = await service.login(
        email="bob@test.com", password="correct_pass"
    )

    assert returned_user.id == 2
    assert isinstance(access_token, str)
    assert isinstance(refresh_token, str)


async def test_login_wrong_password_raises():
    service_temp = make_auth_service()
    hashed = service_temp.hash_password("correct_pass")

    user_repo = AsyncMock()
    user = User(id=2, name="Bob", email="bob@test.com", hashed_password=hashed)
    user_repo.get_by_email.return_value = user

    service = make_auth_service(user_repo)
    with pytest.raises(InvalidCredentialsError):
        await service.login(email="bob@test.com", password="wrong_pass")


async def test_login_unknown_email_raises():
    user_repo = AsyncMock()
    user_repo.get_by_email.return_value = None

    service = make_auth_service(user_repo)
    with pytest.raises(InvalidCredentialsError):
        await service.login(email="nobody@test.com", password="pass")


# ─── refresh ──────────────────────────────────────────────────────────────────

async def test_refresh_returns_new_access_token():
    service = make_auth_service()
    user = User(id=3, name="Carol", email="carol@test.com", hashed_password="x")
    refresh_token_str, jti = service.create_refresh_token(user)

    rt_repo = AsyncMock()
    expires = datetime.now(timezone.utc) + timedelta(days=7)
    rt_record = RefreshToken(
        id=1, user_id=3, token_jti=jti, expires_at=expires, revoked_at=None
    )
    rt_repo.get_by_jti.return_value = rt_record

    user_repo = AsyncMock()
    user_repo.get_by_id.return_value = user

    service2 = make_auth_service(user_repo, rt_repo)
    new_access_token = await service2.refresh(refresh_token_str)
    assert isinstance(new_access_token, str)


async def test_refresh_with_invalid_token_raises():
    service = make_auth_service()
    with pytest.raises(InvalidTokenError):
        await service.refresh("not.valid.token")


async def test_refresh_with_revoked_token_raises():
    service_temp = make_auth_service()
    user = User(id=3, name="Carol", email="carol@test.com", hashed_password="x")
    refresh_token_str, jti = service_temp.create_refresh_token(user)

    rt_repo = AsyncMock()
    revoked_record = RefreshToken(
        id=1, user_id=3, token_jti=jti,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        revoked_at=datetime.now(timezone.utc),
    )
    rt_repo.get_by_jti.return_value = revoked_record

    service = make_auth_service(AsyncMock(), rt_repo)
    with pytest.raises(InvalidTokenError):
        await service.refresh(refresh_token_str)


async def test_refresh_with_access_token_raises():
    """An access token must not be accepted by refresh."""
    service_temp = make_auth_service()
    user = User(id=5, name="Dave", email="dave@test.com", hashed_password="x")
    access_token = service_temp.create_access_token(user)

    service = make_auth_service()
    with pytest.raises(InvalidTokenError):
        await service.refresh(access_token)


# ─── logout ───────────────────────────────────────────────────────────────────

async def test_logout_revokes_all_tokens():
    rt_repo = AsyncMock()
    rt_repo.revoke_by_user_id.return_value = None

    service = make_auth_service(AsyncMock(), rt_repo)
    await service.logout(user_id=5)

    rt_repo.revoke_by_user_id.assert_awaited_once_with(5)
