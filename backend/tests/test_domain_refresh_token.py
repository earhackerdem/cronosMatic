"""Tests for RefreshToken domain entity and repository interface."""

import inspect
from datetime import datetime

from app.domain.refresh_token.entity import RefreshToken
from app.domain.refresh_token.repository import RefreshTokenRepositoryInterface


def test_refresh_token_entity_basic_construction():
    expires = datetime.now()
    token = RefreshToken(user_id=1, token_jti="some-jti", expires_at=expires)
    assert token.user_id == 1
    assert token.token_jti == "some-jti"
    assert token.expires_at == expires


def test_refresh_token_entity_default_values():
    expires = datetime.now()
    token = RefreshToken(user_id=1, token_jti="jti-abc", expires_at=expires)
    assert token.id is None
    assert token.revoked_at is None
    assert token.created_at is None


def test_refresh_token_entity_with_all_fields():
    now = datetime.now()
    token = RefreshToken(
        user_id=5,
        token_jti="jti-xyz",
        expires_at=now,
        id=10,
        revoked_at=now,
        created_at=now,
    )
    assert token.id == 10
    assert token.revoked_at == now
    assert token.created_at == now


def test_refresh_token_entity_is_dataclass():
    import dataclasses

    assert dataclasses.is_dataclass(RefreshToken)


def test_refresh_token_repository_interface_method_signatures():
    methods = [
        name
        for name, _ in inspect.getmembers(
            RefreshTokenRepositoryInterface, predicate=inspect.isfunction
        )
    ]
    assert "create" in methods
    assert "get_by_jti" in methods
    assert "revoke_by_user_id" in methods
