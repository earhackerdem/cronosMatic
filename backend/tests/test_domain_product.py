"""Domain entity tests for Product."""

from decimal import Decimal

import pytest

from app.domain.product.entity import Product


def test_product_entity_defaults():
    """Product dataclass has correct defaults for optional fields."""
    p = Product(
        category_id=1,
        name="Rolex Explorer",
        slug="rolex-explorer",
        sku="SKU-001",
        price=Decimal("1999.99"),
    )
    assert p.id is None
    assert p.description is None
    assert p.stock_quantity == 0
    assert p.brand is None
    assert p.movement_type is None
    assert p.image_path is None
    assert p.is_active is True
    assert p.created_at is None
    assert p.updated_at is None


def test_product_entity_stores_required_fields():
    """Product stores required fields correctly."""
    p = Product(
        category_id=5,
        name="Omega Seamaster",
        slug="omega-seamaster",
        sku="OMG-001",
        price=Decimal("2500.00"),
    )
    assert p.category_id == 5
    assert p.name == "Omega Seamaster"
    assert p.slug == "omega-seamaster"
    assert p.sku == "OMG-001"
    assert p.price == Decimal("2500.00")


def test_product_entity_requires_mandatory_fields():
    """Missing required fields raise TypeError."""
    with pytest.raises(TypeError):
        Product()  # type: ignore[call-arg]

    with pytest.raises(TypeError):
        Product(category_id=1)  # type: ignore[call-arg]

    with pytest.raises(TypeError):
        Product(category_id=1, name="Watch")  # type: ignore[call-arg]


def test_product_entity_full_construction():
    """Product can be constructed with all fields."""
    from datetime import datetime

    now = datetime.now()
    p = Product(
        id=42,
        category_id=3,
        name="TAG Heuer Carrera",
        slug="tag-heuer-carrera",
        sku="TAG-001",
        description="Iconic chronograph",
        price=Decimal("1500.00"),
        stock_quantity=10,
        brand="TAG Heuer",
        movement_type="Automatic",
        image_path="products/tag-heuer.jpg",
        is_active=False,
        created_at=now,
        updated_at=now,
    )
    assert p.id == 42
    assert p.description == "Iconic chronograph"
    assert p.stock_quantity == 10
    assert p.brand == "TAG Heuer"
    assert p.movement_type == "Automatic"
    assert p.image_path == "products/tag-heuer.jpg"
    assert p.is_active is False
