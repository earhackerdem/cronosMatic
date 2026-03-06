"""Integration tests for ProductRepository against a real PostgreSQL database."""

from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.product.entity import Product
from app.models.category import CategoryModel
from app.repositories.product_repository import ProductRepository


# ─── Helpers ─────────────────────────────────────────────────────────────────


async def _create_category(
    session: AsyncSession, name: str = "Test Category", slug: str = "test-category"
) -> CategoryModel:
    """Insert a category directly for FK purposes."""
    cat = CategoryModel(name=name, slug=slug, is_active=True)
    session.add(cat)
    await session.commit()
    await session.refresh(cat)
    return cat


def _make_product(**overrides) -> Product:
    defaults = dict(
        category_id=1,  # will be overridden in tests
        name="Rolex Explorer",
        slug="rolex-explorer",
        sku="SKU-001",
        price=Decimal("1999.99"),
    )
    defaults.update(overrides)
    return Product(**defaults)


# ─── Tests ───────────────────────────────────────────────────────────────────


async def test_create_and_get_by_id(db_session):
    cat = await _create_category(db_session)
    repo = ProductRepository(db_session)

    product = _make_product(category_id=cat.id)
    created = await repo.create(product)

    assert created.id is not None
    assert created.name == "Rolex Explorer"
    assert created.slug == "rolex-explorer"
    assert created.sku == "SKU-001"
    assert created.price == Decimal("1999.99")
    assert created.category_id == cat.id
    assert created.is_active is True
    assert created.created_at is not None

    fetched = await repo.get_by_id(created.id)
    assert fetched is not None
    assert fetched.id == created.id


async def test_get_by_id_returns_none_for_missing(db_session):
    repo = ProductRepository(db_session)
    result = await repo.get_by_id(99999)
    assert result is None


async def test_get_by_slug(db_session):
    cat = await _create_category(db_session)
    repo = ProductRepository(db_session)

    await repo.create(
        _make_product(category_id=cat.id, slug="test-slug", sku="SKU-002")
    )
    result = await repo.get_by_slug("test-slug")
    assert result is not None
    assert result.slug == "test-slug"


async def test_get_by_slug_returns_none_for_missing(db_session):
    repo = ProductRepository(db_session)
    result = await repo.get_by_slug("nonexistent-slug")
    assert result is None


async def test_get_by_slug_active_returns_active_product(db_session):
    cat = await _create_category(db_session)
    repo = ProductRepository(db_session)

    await repo.create(
        _make_product(
            category_id=cat.id, slug="active-prod", sku="SKU-ACT", is_active=True
        )
    )
    result = await repo.get_by_slug_active("active-prod")
    assert result is not None
    assert result.slug == "active-prod"


async def test_get_by_slug_active_excludes_inactive(db_session):
    cat = await _create_category(db_session)
    repo = ProductRepository(db_session)

    await repo.create(
        _make_product(
            category_id=cat.id, slug="inactive-prod", sku="SKU-INACT", is_active=False
        )
    )
    result = await repo.get_by_slug_active("inactive-prod")
    assert result is None


async def test_get_by_sku(db_session):
    cat = await _create_category(db_session)
    repo = ProductRepository(db_session)

    await repo.create(
        _make_product(category_id=cat.id, slug="sku-test", sku="UNIQUE-SKU")
    )
    result = await repo.get_by_sku("UNIQUE-SKU")
    assert result is not None
    assert result.sku == "UNIQUE-SKU"


async def test_get_by_sku_returns_none_for_missing(db_session):
    repo = ProductRepository(db_session)
    result = await repo.get_by_sku("NON-EXISTENT")
    assert result is None


async def test_list_active_returns_only_active(db_session):
    cat = await _create_category(db_session)
    repo = ProductRepository(db_session)

    await repo.create(
        _make_product(category_id=cat.id, slug="active-1", sku="A1", is_active=True)
    )
    await repo.create(
        _make_product(category_id=cat.id, slug="active-2", sku="A2", is_active=True)
    )
    await repo.create(
        _make_product(category_id=cat.id, slug="inactive-1", sku="I1", is_active=False)
    )

    items, total = await repo.list_active(
        offset=0,
        limit=10,
        category_id=None,
        search=None,
        sort_by="name",
        sort_direction="asc",
    )
    assert total == 2
    assert len(items) == 2


async def test_list_active_filter_by_category(db_session):
    cat1 = await _create_category(db_session, name="Cat 1", slug="cat-1")
    cat2 = await _create_category(db_session, name="Cat 2", slug="cat-2")
    repo = ProductRepository(db_session)

    await repo.create(_make_product(category_id=cat1.id, slug="prod-cat1", sku="PC1"))
    await repo.create(_make_product(category_id=cat2.id, slug="prod-cat2", sku="PC2"))

    items, total = await repo.list_active(
        offset=0,
        limit=10,
        category_id=cat1.id,
        search=None,
        sort_by="name",
        sort_direction="asc",
    )
    assert total == 1
    assert items[0].slug == "prod-cat1"


async def test_list_active_search_by_name(db_session):
    cat = await _create_category(db_session)
    repo = ProductRepository(db_session)

    await repo.create(
        _make_product(
            category_id=cat.id, name="Rolex Submariner", slug="rolex-sub", sku="RS1"
        )
    )
    await repo.create(
        _make_product(
            category_id=cat.id, name="Omega Speedmaster", slug="omega-speed", sku="OS1"
        )
    )

    items, total = await repo.list_active(
        offset=0,
        limit=10,
        category_id=None,
        search="rolex",
        sort_by="name",
        sort_direction="asc",
    )
    assert total == 1
    assert items[0].name == "Rolex Submariner"


async def test_list_active_sort_by_price_desc(db_session):
    cat = await _create_category(db_session)
    repo = ProductRepository(db_session)

    await repo.create(
        _make_product(
            category_id=cat.id, slug="cheap", sku="C1", price=Decimal("100.00")
        )
    )
    await repo.create(
        _make_product(
            category_id=cat.id, slug="expensive", sku="E1", price=Decimal("9999.00")
        )
    )

    items, total = await repo.list_active(
        offset=0,
        limit=10,
        category_id=None,
        search=None,
        sort_by="price",
        sort_direction="desc",
    )
    assert total == 2
    assert items[0].price == Decimal("9999.00")
    assert items[1].price == Decimal("100.00")


async def test_list_active_pagination(db_session):
    cat = await _create_category(db_session)
    repo = ProductRepository(db_session)

    for i in range(5):
        await repo.create(
            _make_product(category_id=cat.id, slug=f"prod-{i}", sku=f"SKU-{i}")
        )

    items, total = await repo.list_active(
        offset=2,
        limit=2,
        category_id=None,
        search=None,
        sort_by="name",
        sort_direction="asc",
    )
    assert total == 5
    assert len(items) == 2


async def test_list_all_includes_inactive(db_session):
    cat = await _create_category(db_session)
    repo = ProductRepository(db_session)

    await repo.create(
        _make_product(category_id=cat.id, slug="active-all", sku="AA1", is_active=True)
    )
    await repo.create(
        _make_product(
            category_id=cat.id, slug="inactive-all", sku="IA1", is_active=False
        )
    )

    items, total = await repo.list_all(offset=0, limit=10)
    assert total == 2
    assert len(items) == 2


async def test_update_product(db_session):
    cat = await _create_category(db_session)
    repo = ProductRepository(db_session)

    created = await repo.create(_make_product(category_id=cat.id))
    created.name = "Updated Name"
    created.price = Decimal("2999.99")

    updated = await repo.update(created)
    assert updated.name == "Updated Name"
    assert updated.price == Decimal("2999.99")


async def test_delete_product(db_session):
    cat = await _create_category(db_session)
    repo = ProductRepository(db_session)

    created = await repo.create(_make_product(category_id=cat.id))
    product_id = created.id

    result = await repo.delete(product_id)
    assert result is True

    fetched = await repo.get_by_id(product_id)
    assert fetched is None


async def test_delete_returns_false_for_missing(db_session):
    repo = ProductRepository(db_session)
    result = await repo.delete(99999)
    assert result is False


async def test_unique_constraint_slug(db_session):
    cat = await _create_category(db_session)
    repo = ProductRepository(db_session)

    await repo.create(_make_product(category_id=cat.id, slug="dup-slug", sku="DUP-1"))
    with pytest.raises(Exception):
        await repo.create(
            _make_product(category_id=cat.id, slug="dup-slug", sku="DUP-2")
        )


async def test_unique_constraint_sku(db_session):
    cat = await _create_category(db_session)
    repo = ProductRepository(db_session)

    await repo.create(_make_product(category_id=cat.id, slug="slug-1", sku="DUP-SKU"))
    with pytest.raises(Exception):
        await repo.create(
            _make_product(category_id=cat.id, slug="slug-2", sku="DUP-SKU")
        )


async def test_list_active_includes_category_data(db_session):
    """list_active eagerly loads the related category."""
    cat = await _create_category(
        db_session, name="Luxury Watches", slug="luxury-watches"
    )
    repo = ProductRepository(db_session)

    await repo.create(
        _make_product(category_id=cat.id, slug="prod-with-cat", sku="PWC-1")
    )

    items, _ = await repo.list_active(
        offset=0,
        limit=10,
        category_id=None,
        search=None,
        sort_by="name",
        sort_direction="asc",
    )
    assert len(items) == 1
    # The domain entity has category_id loaded
    assert items[0].category_id == cat.id
