"""Integration tests for CategoryRepository."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.db.base import Base
from app.domain.category.entity import Category
from app.repositories.category_repository import CategoryRepository


@pytest.fixture
async def repo_session():
    """Per-test async DB session for category repository tests."""
    engine = create_async_engine(settings.database_url, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    # Clean up categories table after each test
    async with engine.begin() as conn:
        await conn.execute(text("TRUNCATE TABLE categories RESTART IDENTITY CASCADE"))

    await engine.dispose()


def _make_category(name: str, slug: str, **kwargs) -> Category:
    return Category(name=name, slug=slug, **kwargs)


async def test_repository_create_and_retrieve_by_id(repo_session):
    repo = CategoryRepository(repo_session)
    cat = _make_category("Pocket Watches", "pocket-watches")
    created = await repo.create(cat)

    assert created.id is not None
    assert isinstance(created.id, int)
    assert created.name == "Pocket Watches"
    assert created.slug == "pocket-watches"
    assert created.is_active is True

    fetched = await repo.get_by_id(created.id)
    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.name == "Pocket Watches"


async def test_repository_get_by_slug_returns_entity(repo_session):
    repo = CategoryRepository(repo_session)
    cat = _make_category("Dress Watches", "dress-watches")
    await repo.create(cat)

    fetched = await repo.get_by_slug("dress-watches")
    assert fetched is not None
    assert fetched.slug == "dress-watches"
    assert fetched.name == "Dress Watches"


async def test_repository_get_by_slug_active_excludes_inactive(repo_session):
    repo = CategoryRepository(repo_session)
    cat = _make_category("Inactive Cat", "inactive-cat", is_active=False)
    await repo.create(cat)

    result = await repo.get_by_slug_active("inactive-cat")
    assert result is None


async def test_repository_get_by_slug_active_returns_active(repo_session):
    repo = CategoryRepository(repo_session)
    cat = _make_category("Active Cat", "active-cat", is_active=True)
    await repo.create(cat)

    result = await repo.get_by_slug_active("active-cat")
    assert result is not None
    assert result.slug == "active-cat"


async def test_repository_list_active_excludes_inactive(repo_session):
    repo = CategoryRepository(repo_session)
    await repo.create(_make_category("Active", "active-1", is_active=True))
    await repo.create(_make_category("Inactive", "inactive-1", is_active=False))

    items, total = await repo.list_active(offset=0, limit=10)
    assert total == 1
    assert len(items) == 1
    assert items[0].name == "Active"


async def test_repository_list_active_pagination(repo_session):
    repo = CategoryRepository(repo_session)
    for i in range(5):
        await repo.create(_make_category(f"Cat {i}", f"cat-{i}", is_active=True))

    items, total = await repo.list_active(offset=2, limit=2)
    assert total == 5
    assert len(items) == 2


async def test_repository_list_all_includes_inactive(repo_session):
    repo = CategoryRepository(repo_session)
    await repo.create(_make_category("Active", "all-active", is_active=True))
    await repo.create(_make_category("Inactive", "all-inactive", is_active=False))

    items, total = await repo.list_all(offset=0, limit=10)
    assert total == 2
    assert len(items) == 2


async def test_repository_update_persists_changes(repo_session):
    repo = CategoryRepository(repo_session)
    created = await repo.create(_make_category("Old Name", "old-slug"))
    created.name = "New Name"
    created.slug = "new-slug"

    updated = await repo.update(created)
    assert updated.name == "New Name"
    assert updated.slug == "new-slug"

    refetched = await repo.get_by_id(created.id)
    assert refetched.name == "New Name"


async def test_repository_set_inactive_returns_true(repo_session):
    repo = CategoryRepository(repo_session)
    created = await repo.create(_make_category("Active Cat", "active-cat-del"))

    result = await repo.set_inactive(created.id)
    assert result is True

    fetched = await repo.get_by_id(created.id)
    assert fetched is not None
    assert fetched.is_active is False


async def test_repository_set_inactive_returns_false_for_missing_id(repo_session):
    repo = CategoryRepository(repo_session)
    result = await repo.set_inactive(99999)
    assert result is False


async def test_repository_slug_unique_constraint(repo_session):
    repo = CategoryRepository(repo_session)
    await repo.create(_make_category("First", "same-slug"))

    with pytest.raises(IntegrityError):
        await repo.create(_make_category("Second", "same-slug"))
