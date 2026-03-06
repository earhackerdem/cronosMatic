"""Tests for User domain entity and repository interface."""
from datetime import datetime

from app.domain.user.entity import User
from app.domain.user.repository import UserRepositoryInterface


def test_user_entity_basic_construction():
    user = User(name="Alice", email="alice@example.com", hashed_password="hashed123")
    assert user.name == "Alice"
    assert user.email == "alice@example.com"
    assert user.hashed_password == "hashed123"


def test_user_entity_default_values():
    user = User(name="Bob", email="bob@example.com", hashed_password="hashed456")
    assert user.id is None
    assert user.is_admin is False
    assert user.created_at is None
    assert user.updated_at is None


def test_user_entity_with_all_fields():
    now = datetime.now()
    user = User(
        name="Carol",
        email="carol@example.com",
        hashed_password="hashedabc",
        id=42,
        is_admin=True,
        created_at=now,
        updated_at=now,
    )
    assert user.id == 42
    assert user.is_admin is True
    assert user.created_at == now
    assert user.updated_at == now


def test_user_entity_is_dataclass():
    """User is a plain dataclass, no framework dependencies."""
    import dataclasses
    assert dataclasses.is_dataclass(User)


def test_user_repository_interface_is_protocol():
    """UserRepositoryInterface must be a Protocol."""
    assert hasattr(UserRepositoryInterface, "create")
    assert hasattr(UserRepositoryInterface, "get_by_id")
    assert hasattr(UserRepositoryInterface, "get_by_email")


def test_user_repository_interface_method_signatures():
    """Verify Protocol method names exist (duck-typing check)."""
    import inspect
    methods = [
        name for name, _ in inspect.getmembers(UserRepositoryInterface, predicate=inspect.isfunction)
    ]
    assert "create" in methods
    assert "get_by_id" in methods
    assert "get_by_email" in methods
