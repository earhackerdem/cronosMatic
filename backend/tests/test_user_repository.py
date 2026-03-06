"""Integration tests for UserRepository against a real database."""

from app.domain.user.entity import User
from app.repositories.user_repository import UserRepository


async def test_create_user(db_session):
    repo = UserRepository(db_session)
    user = User(name="Alice", email="alice@repo.test", hashed_password="hashed123")
    created = await repo.create(user)
    assert created.id is not None
    assert created.name == "Alice"
    assert created.email == "alice@repo.test"
    assert created.hashed_password == "hashed123"


async def test_get_by_id(db_session):
    repo = UserRepository(db_session)
    user = User(name="Bob", email="bob@repo.test", hashed_password="hashed456")
    created = await repo.create(user)

    found = await repo.get_by_id(created.id)
    assert found is not None
    assert found.id == created.id
    assert found.email == "bob@repo.test"


async def test_get_by_id_not_found(db_session):
    repo = UserRepository(db_session)
    result = await repo.get_by_id(999999)
    assert result is None


async def test_get_by_email(db_session):
    repo = UserRepository(db_session)
    user = User(name="Carol", email="carol@repo.test", hashed_password="hashedabc")
    await repo.create(user)

    found = await repo.get_by_email("carol@repo.test")
    assert found is not None
    assert found.name == "Carol"


async def test_get_by_email_not_found(db_session):
    repo = UserRepository(db_session)
    result = await repo.get_by_email("nonexistent@repo.test")
    assert result is None


async def test_created_user_hashed_password_mapped_correctly(db_session):
    """ORM model uses 'password' column, domain uses 'hashed_password' — verify mapping."""
    repo = UserRepository(db_session)
    user = User(name="Dave", email="dave@repo.test", hashed_password="supersecret")
    created = await repo.create(user)
    assert created.hashed_password == "supersecret"
