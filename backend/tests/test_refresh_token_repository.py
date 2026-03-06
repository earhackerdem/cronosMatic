"""Integration tests for RefreshTokenRepository against a real database."""

from datetime import datetime, timedelta, timezone


from app.domain.refresh_token.entity import RefreshToken
from app.domain.user.entity import User
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository


async def _create_user(db_session, email: str) -> User:
    repo = UserRepository(db_session)
    user = User(name="Test User", email=email, hashed_password="hashed")
    return await repo.create(user)


async def test_create_refresh_token(db_session):
    user = await _create_user(db_session, "rt_alice@test.test")
    repo = RefreshTokenRepository(db_session)
    expires = datetime.now(timezone.utc) + timedelta(days=7)
    token = RefreshToken(user_id=user.id, token_jti="jti-create", expires_at=expires)
    created = await repo.create(token)
    assert created.id is not None
    assert created.token_jti == "jti-create"
    assert created.user_id == user.id
    assert created.revoked_at is None


async def test_get_by_jti(db_session):
    user = await _create_user(db_session, "rt_bob@test.test")
    repo = RefreshTokenRepository(db_session)
    expires = datetime.now(timezone.utc) + timedelta(days=7)
    token = RefreshToken(user_id=user.id, token_jti="jti-getbyjti", expires_at=expires)
    created = await repo.create(token)

    found = await repo.get_by_jti("jti-getbyjti")
    assert found is not None
    assert found.id == created.id


async def test_get_by_jti_not_found(db_session):
    repo = RefreshTokenRepository(db_session)
    result = await repo.get_by_jti("nonexistent-jti")
    assert result is None


async def test_revoke_by_user_id(db_session):
    user = await _create_user(db_session, "rt_carol@test.test")
    repo = RefreshTokenRepository(db_session)
    expires = datetime.now(timezone.utc) + timedelta(days=7)

    token1 = RefreshToken(user_id=user.id, token_jti="jti-revoke-1", expires_at=expires)
    token2 = RefreshToken(user_id=user.id, token_jti="jti-revoke-2", expires_at=expires)
    await repo.create(token1)
    await repo.create(token2)

    await repo.revoke_by_user_id(user.id)

    t1 = await repo.get_by_jti("jti-revoke-1")
    t2 = await repo.get_by_jti("jti-revoke-2")
    assert t1 is not None and t1.revoked_at is not None
    assert t2 is not None and t2.revoked_at is not None


async def test_revoke_by_user_id_no_tokens(db_session):
    """revoke_by_user_id should not fail if no tokens exist."""
    repo = RefreshTokenRepository(db_session)
    # Should complete without error
    await repo.revoke_by_user_id(999999)
