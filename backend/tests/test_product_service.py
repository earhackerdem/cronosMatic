"""Unit tests for ProductService with mocked repositories."""

from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from app.domain.category.entity import Category
from app.domain.product.entity import Product
from app.services.product import (
    ProductCategoryNotFoundError,
    ProductConflictError,
    ProductService,
)


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _make_product(**overrides) -> Product:
    defaults = dict(
        id=1,
        category_id=1,
        name="Rolex Explorer",
        slug="rolex-explorer",
        sku="SKU-001",
        price=Decimal("1999.99"),
        is_active=True,
    )
    defaults.update(overrides)
    return Product(**defaults)


def _make_category(**overrides) -> Category:
    defaults = dict(id=1, name="Luxury", slug="luxury", is_active=True)
    defaults.update(overrides)
    return Category(**defaults)


def _make_service(product_repo=None, category_repo=None) -> ProductService:
    if product_repo is None:
        product_repo = AsyncMock()
    if category_repo is None:
        category_repo = AsyncMock()
    return ProductService(product_repo, category_repo)


# ─── list_active ─────────────────────────────────────────────────────────────


async def test_list_active_no_category_filter():
    repo = AsyncMock()
    repo.list_active.return_value = ([_make_product()], 1)
    cat_repo = AsyncMock()
    service = _make_service(repo, cat_repo)

    items, total = await service.list_active(page=1, size=10, category_slug=None, search=None, sort_by="name", sort_direction="asc")
    assert total == 1
    repo.list_active.assert_awaited_once_with(
        offset=0, limit=10, category_id=None, search=None, sort_by="name", sort_direction="asc"
    )


async def test_list_active_with_category_slug_resolves_to_category_id():
    cat = _make_category(id=42, slug="luxury")
    repo = AsyncMock()
    repo.list_active.return_value = ([_make_product(category_id=42)], 1)
    cat_repo = AsyncMock()
    cat_repo.get_by_slug_active.return_value = cat

    service = _make_service(repo, cat_repo)
    items, total = await service.list_active(page=1, size=10, category_slug="luxury", search=None, sort_by="name", sort_direction="asc")

    cat_repo.get_by_slug_active.assert_awaited_once_with("luxury")
    repo.list_active.assert_awaited_once_with(
        offset=0, limit=10, category_id=42, search=None, sort_by="name", sort_direction="asc"
    )


async def test_list_active_category_not_found_raises_error():
    repo = AsyncMock()
    cat_repo = AsyncMock()
    cat_repo.get_by_slug_active.return_value = None
    service = _make_service(repo, cat_repo)

    with pytest.raises(ProductCategoryNotFoundError):
        await service.list_active(page=1, size=10, category_slug="nonexistent", search=None, sort_by="name", sort_direction="asc")


# ─── list_all_admin ───────────────────────────────────────────────────────────


async def test_list_all_admin():
    repo = AsyncMock()
    repo.list_all.return_value = ([_make_product(), _make_product(id=2, is_active=False)], 2)
    service = _make_service(repo)

    items, total = await service.list_all_admin(page=1, size=15)
    assert total == 2
    repo.list_all.assert_awaited_once_with(offset=0, limit=15)


# ─── get_active_by_slug ───────────────────────────────────────────────────────


async def test_get_active_by_slug_returns_product():
    product = _make_product()
    repo = AsyncMock()
    repo.get_by_slug_active.return_value = product
    service = _make_service(repo)

    result = await service.get_active_by_slug("rolex-explorer")
    assert result == product


async def test_get_active_by_slug_returns_none_when_missing():
    repo = AsyncMock()
    repo.get_by_slug_active.return_value = None
    service = _make_service(repo)

    result = await service.get_active_by_slug("missing-slug")
    assert result is None


# ─── get_by_id ────────────────────────────────────────────────────────────────


async def test_get_by_id_returns_product():
    product = _make_product()
    repo = AsyncMock()
    repo.get_by_id.return_value = product
    service = _make_service(repo)

    result = await service.get_by_id(1)
    assert result == product


async def test_get_by_id_returns_none_for_missing():
    repo = AsyncMock()
    repo.get_by_id.return_value = None
    service = _make_service(repo)

    result = await service.get_by_id(99999)
    assert result is None


# ─── create_product ───────────────────────────────────────────────────────────


async def test_create_product_success():
    cat = _make_category()
    product = _make_product()
    repo = AsyncMock()
    repo.get_by_slug.return_value = None
    repo.get_by_sku.return_value = None
    repo.create.return_value = product
    cat_repo = AsyncMock()
    cat_repo.get_by_id.return_value = cat
    service = _make_service(repo, cat_repo)

    result = await service.create_product({
        "category_id": 1,
        "name": "Rolex Explorer",
        "sku": "SKU-001",
        "price": Decimal("1999.99"),
    })
    assert result == product
    repo.create.assert_awaited_once()


async def test_create_product_auto_generates_slug():
    cat = _make_category()
    repo = AsyncMock()
    repo.get_by_slug.return_value = None
    repo.get_by_sku.return_value = None
    repo.create.return_value = _make_product(slug="rolex-explorer")
    cat_repo = AsyncMock()
    cat_repo.get_by_id.return_value = cat
    service = _make_service(repo, cat_repo)

    await service.create_product({
        "category_id": 1,
        "name": "Rolex Explorer",
        "sku": "SKU-001",
        "price": Decimal("1999.99"),
        # no slug provided
    })

    # The entity passed to repo.create should have a slug derived from name
    created_entity = repo.create.call_args[0][0]
    assert created_entity.slug == "rolex-explorer"


async def test_create_product_uses_provided_slug():
    cat = _make_category()
    repo = AsyncMock()
    repo.get_by_slug.return_value = None
    repo.get_by_sku.return_value = None
    repo.create.return_value = _make_product(slug="custom-slug")
    cat_repo = AsyncMock()
    cat_repo.get_by_id.return_value = cat
    service = _make_service(repo, cat_repo)

    await service.create_product({
        "category_id": 1,
        "name": "Rolex Explorer",
        "slug": "custom-slug",
        "sku": "SKU-001",
        "price": Decimal("1999.99"),
    })
    created_entity = repo.create.call_args[0][0]
    assert created_entity.slug == "custom-slug"


async def test_create_product_category_not_found():
    repo = AsyncMock()
    cat_repo = AsyncMock()
    cat_repo.get_by_id.return_value = None
    service = _make_service(repo, cat_repo)

    with pytest.raises(ProductCategoryNotFoundError):
        await service.create_product({
            "category_id": 999,
            "name": "Watch",
            "sku": "SKU-X",
            "price": Decimal("100.00"),
        })


async def test_create_product_slug_conflict():
    cat = _make_category()
    repo = AsyncMock()
    repo.get_by_slug.return_value = _make_product()  # already exists
    cat_repo = AsyncMock()
    cat_repo.get_by_id.return_value = cat
    service = _make_service(repo, cat_repo)

    with pytest.raises(ProductConflictError):
        await service.create_product({
            "category_id": 1,
            "name": "Rolex",
            "slug": "rolex-explorer",
            "sku": "NEW-SKU",
            "price": Decimal("100.00"),
        })


async def test_create_product_sku_conflict():
    cat = _make_category()
    repo = AsyncMock()
    repo.get_by_slug.return_value = None
    repo.get_by_sku.return_value = _make_product()  # SKU already exists
    cat_repo = AsyncMock()
    cat_repo.get_by_id.return_value = cat
    service = _make_service(repo, cat_repo)

    with pytest.raises(ProductConflictError):
        await service.create_product({
            "category_id": 1,
            "name": "New Watch",
            "sku": "SKU-001",
            "price": Decimal("100.00"),
        })


# ─── update_product ───────────────────────────────────────────────────────────


async def test_update_product_success():
    existing = _make_product()
    updated = _make_product(name="Updated Name")
    repo = AsyncMock()
    repo.get_by_id.return_value = existing
    repo.update.return_value = updated
    cat_repo = AsyncMock()
    cat_repo.get_by_id.return_value = _make_category()
    service = _make_service(repo, cat_repo)

    result = await service.update_product(1, {"name": "Updated Name"})
    assert result == updated


async def test_update_product_not_found_returns_none():
    repo = AsyncMock()
    repo.get_by_id.return_value = None
    service = _make_service(repo)

    result = await service.update_product(99999, {"name": "Whatever"})
    assert result is None


async def test_update_product_slug_conflict():
    existing = _make_product(slug="original-slug")
    repo = AsyncMock()
    repo.get_by_id.return_value = existing
    repo.get_by_slug.return_value = _make_product(id=99, slug="taken-slug")  # taken by another product
    service = _make_service(repo)

    with pytest.raises(ProductConflictError):
        await service.update_product(1, {"slug": "taken-slug"})


async def test_update_product_sku_conflict():
    existing = _make_product(sku="OLD-SKU")
    repo = AsyncMock()
    repo.get_by_id.return_value = existing
    repo.get_by_sku.return_value = _make_product(id=99, sku="TAKEN-SKU")  # taken by another product
    service = _make_service(repo)

    with pytest.raises(ProductConflictError):
        await service.update_product(1, {"sku": "TAKEN-SKU"})


async def test_update_product_no_conflict_for_same_slug():
    """Updating slug to the same value should not raise conflict."""
    existing = _make_product(id=1, slug="my-slug")
    repo = AsyncMock()
    repo.get_by_id.return_value = existing
    repo.get_by_slug.return_value = existing  # same object — same id
    repo.update.return_value = existing
    service = _make_service(repo)

    result = await service.update_product(1, {"slug": "my-slug"})
    assert result is not None


async def test_update_product_category_not_found():
    existing = _make_product()
    repo = AsyncMock()
    repo.get_by_id.return_value = existing
    cat_repo = AsyncMock()
    cat_repo.get_by_id.return_value = None  # category not found
    service = _make_service(repo, cat_repo)

    with pytest.raises(ProductCategoryNotFoundError):
        await service.update_product(1, {"category_id": 999})


# ─── delete_product ───────────────────────────────────────────────────────────


async def test_delete_product_success():
    repo = AsyncMock()
    repo.delete.return_value = True
    service = _make_service(repo)

    result = await service.delete_product(1)
    assert result is True
    repo.delete.assert_awaited_once_with(1)


async def test_delete_product_not_found():
    repo = AsyncMock()
    repo.delete.return_value = False
    service = _make_service(repo)

    result = await service.delete_product(99999)
    assert result is False


# ─── _generate_slug ───────────────────────────────────────────────────────────


def test_generate_slug_basic():
    service = _make_service()
    assert service._generate_slug("Rolex Explorer") == "rolex-explorer"


def test_generate_slug_special_chars():
    service = _make_service()
    assert service._generate_slug("TAG Heuer & Carrera") == "tag-heuer-carrera"


def test_generate_slug_multiple_spaces():
    service = _make_service()
    assert service._generate_slug("  Watch  Pro  ") == "watch-pro"
