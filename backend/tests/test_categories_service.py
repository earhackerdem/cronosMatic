"""Unit tests for CategoryService with mocked repository."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.exc import IntegrityError

from app.domain.category.entity import Category
from app.services.category import CategoryConflictError, CategoryService


def _make_mock_repo():
    repo = MagicMock()
    repo.create = AsyncMock()
    repo.get_by_id = AsyncMock()
    repo.get_by_slug = AsyncMock()
    repo.get_by_slug_active = AsyncMock()
    repo.list_active = AsyncMock()
    repo.list_all = AsyncMock()
    repo.update = AsyncMock()
    repo.set_inactive = AsyncMock()
    return repo


def _make_cat(**kwargs) -> Category:
    defaults = dict(id=1, name="Test Cat", slug="test-cat", is_active=True)
    defaults.update(kwargs)
    return Category(**defaults)


# ─── list_active ─────────────────────────────────────────────────────────────


async def test_list_active_returns_paginated_tuple():
    repo = _make_mock_repo()
    cats = [_make_cat(id=i, slug=f"cat-{i}") for i in range(3)]
    repo.list_active.return_value = (cats, 3)

    service = CategoryService(repo)
    items, total = await service.list_active(page=1, size=3)

    repo.list_active.assert_called_once_with(offset=0, limit=3)
    assert total == 3
    assert len(items) == 3


async def test_list_active_page_2_computes_correct_offset():
    repo = _make_mock_repo()
    repo.list_active.return_value = ([], 10)

    service = CategoryService(repo)
    await service.list_active(page=2, size=5)

    repo.list_active.assert_called_once_with(offset=5, limit=5)


# ─── list_all_admin ──────────────────────────────────────────────────────────


async def test_list_all_admin_returns_all_including_inactive():
    repo = _make_mock_repo()
    cats = [_make_cat(id=1), _make_cat(id=2, is_active=False, slug="cat-2")]
    repo.list_all.return_value = (cats, 2)

    service = CategoryService(repo)
    items, total = await service.list_all_admin(page=1, size=15)

    repo.list_all.assert_called_once_with(offset=0, limit=15)
    assert total == 2


# ─── get_active_by_slug ──────────────────────────────────────────────────────


async def test_get_active_by_slug_returns_category():
    repo = _make_mock_repo()
    cat = _make_cat()
    repo.get_by_slug_active.return_value = cat

    service = CategoryService(repo)
    result = await service.get_active_by_slug("test-cat")

    assert result is cat
    repo.get_by_slug_active.assert_called_once_with("test-cat")


async def test_get_active_by_slug_returns_none_when_not_found():
    repo = _make_mock_repo()
    repo.get_by_slug_active.return_value = None

    service = CategoryService(repo)
    result = await service.get_active_by_slug("missing")

    assert result is None


# ─── get_by_id ───────────────────────────────────────────────────────────────


async def test_get_by_id_returns_category():
    repo = _make_mock_repo()
    cat = _make_cat()
    repo.get_by_id.return_value = cat

    service = CategoryService(repo)
    result = await service.get_by_id(1)

    assert result is cat
    repo.get_by_id.assert_called_once_with(1)


async def test_get_by_id_returns_none_when_missing():
    repo = _make_mock_repo()
    repo.get_by_id.return_value = None

    service = CategoryService(repo)
    result = await service.get_by_id(999)

    assert result is None


# ─── create_category ─────────────────────────────────────────────────────────


async def test_create_category_success():
    repo = _make_mock_repo()
    repo.get_by_slug.return_value = None
    created = _make_cat()
    repo.create.return_value = created

    service = CategoryService(repo)
    result = await service.create_category(
        name="Test Cat", slug="test-cat", description=None, image_path=None, is_active=True
    )

    assert result is created
    repo.create.assert_called_once()


async def test_create_category_raises_conflict_on_duplicate_slug():
    repo = _make_mock_repo()
    repo.get_by_slug.return_value = _make_cat()  # slug already exists

    service = CategoryService(repo)
    with pytest.raises(CategoryConflictError):
        await service.create_category(
            name="Dup", slug="test-cat", description=None, image_path=None, is_active=True
        )

    repo.create.assert_not_called()


async def test_create_category_wraps_integrity_error():
    repo = _make_mock_repo()
    repo.get_by_slug.return_value = None
    repo.create.side_effect = IntegrityError(None, None, Exception("unique"))

    service = CategoryService(repo)
    with pytest.raises(CategoryConflictError):
        await service.create_category(
            name="Dup", slug="test-cat", description=None, image_path=None, is_active=True
        )


# ─── update_category ─────────────────────────────────────────────────────────


async def test_update_category_returns_updated():
    repo = _make_mock_repo()
    existing = _make_cat(name="Old", slug="old-slug")
    repo.get_by_id.return_value = existing
    updated = _make_cat(name="New", slug="old-slug")
    repo.update.return_value = updated

    service = CategoryService(repo)
    result = await service.update_category(1, {"name": "New"})

    assert result is updated
    repo.update.assert_called_once()


async def test_update_category_returns_none_when_not_found():
    repo = _make_mock_repo()
    repo.get_by_id.return_value = None

    service = CategoryService(repo)
    result = await service.update_category(999, {"name": "X"})

    assert result is None
    repo.update.assert_not_called()


async def test_update_category_raises_conflict_on_slug_collision():
    repo = _make_mock_repo()
    existing = _make_cat(id=1, slug="old-slug")
    repo.get_by_id.return_value = existing
    # Another category already owns the new slug
    repo.get_by_slug.return_value = _make_cat(id=2, slug="new-slug")

    service = CategoryService(repo)
    with pytest.raises(CategoryConflictError):
        await service.update_category(1, {"slug": "new-slug"})

    repo.update.assert_not_called()


async def test_update_category_no_slug_change_skips_uniqueness_check():
    repo = _make_mock_repo()
    existing = _make_cat(id=1, slug="same-slug")
    repo.get_by_id.return_value = existing
    repo.update.return_value = existing

    service = CategoryService(repo)
    # slug not in data dict → no uniqueness check
    await service.update_category(1, {"name": "New Name"})

    repo.get_by_slug.assert_not_called()
    repo.update.assert_called_once()


async def test_update_category_same_slug_skips_uniqueness_check():
    repo = _make_mock_repo()
    existing = _make_cat(id=1, slug="same-slug")
    repo.get_by_id.return_value = existing
    repo.update.return_value = existing

    service = CategoryService(repo)
    # slug is in data but unchanged → no uniqueness check
    await service.update_category(1, {"slug": "same-slug"})

    repo.get_by_slug.assert_not_called()
    repo.update.assert_called_once()


# ─── delete_category ─────────────────────────────────────────────────────────


async def test_delete_category_sets_inactive():
    repo = _make_mock_repo()
    repo.set_inactive.return_value = True

    service = CategoryService(repo)
    result = await service.delete_category(1)

    assert result is True
    repo.set_inactive.assert_called_once_with(1)


async def test_delete_category_returns_false_when_not_found():
    repo = _make_mock_repo()
    repo.set_inactive.return_value = False

    service = CategoryService(repo)
    result = await service.delete_category(999)

    assert result is False
