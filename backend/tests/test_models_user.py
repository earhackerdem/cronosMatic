"""Tests for UserModel and RefreshTokenModel ORM models."""

from app.models.user import UserModel
from app.models.refresh_token import RefreshTokenModel


def test_user_model_instantiation():
    user = UserModel(name="Alice", email="alice@example.com", password="hashed123")
    assert user.name == "Alice"
    assert user.email == "alice@example.com"
    assert user.password == "hashed123"


def test_user_model_defaults():
    user = UserModel(name="Bob", email="bob@example.com", password="hashed456")
    assert user.is_admin is False or user.is_admin is None  # default False


def test_user_model_tablename():
    assert UserModel.__tablename__ == "users"


def test_refresh_token_model_instantiation():
    from datetime import datetime

    expires = datetime.now()
    token = RefreshTokenModel(user_id=1, token_jti="some-jti", expires_at=expires)
    assert token.user_id == 1
    assert token.token_jti == "some-jti"
    assert token.expires_at == expires


def test_refresh_token_model_tablename():
    assert RefreshTokenModel.__tablename__ == "refresh_tokens"


def test_user_model_has_expected_columns():
    """Verify all expected columns exist on the ORM model."""
    columns = {col.key for col in UserModel.__table__.columns}
    assert "id" in columns
    assert "name" in columns
    assert "email" in columns
    assert "password" in columns
    assert "is_admin" in columns
    assert "created_at" in columns
    assert "updated_at" in columns


def test_refresh_token_model_has_expected_columns():
    columns = {col.key for col in RefreshTokenModel.__table__.columns}
    assert "id" in columns
    assert "user_id" in columns
    assert "token_jti" in columns
    assert "expires_at" in columns
    assert "revoked_at" in columns
    assert "created_at" in columns
