"""Unit tests for the Category domain entity and repository protocol."""

from datetime import datetime

from app.domain.category.entity import Category


def test_category_minimal_construction():
    """Category requires only name and slug."""
    cat = Category(name="Pocket Watches", slug="pocket-watches")
    assert cat.name == "Pocket Watches"
    assert cat.slug == "pocket-watches"
    assert cat.description is None
    assert cat.image_path is None
    assert cat.is_active is True
    assert cat.id is None
    assert cat.created_at is None
    assert cat.updated_at is None


def test_category_full_construction():
    """Category accepts all optional fields."""
    now = datetime.utcnow()
    cat = Category(
        id=1,
        name="Dress Watches",
        slug="dress-watches",
        description="Elegant dress watches",
        image_path="categories/dress.jpg",
        is_active=False,
        created_at=now,
        updated_at=now,
    )
    assert cat.id == 1
    assert cat.name == "Dress Watches"
    assert cat.slug == "dress-watches"
    assert cat.description == "Elegant dress watches"
    assert cat.image_path == "categories/dress.jpg"
    assert cat.is_active is False
    assert cat.created_at == now
    assert cat.updated_at == now


def test_category_is_active_defaults_to_true():
    cat = Category(name="Sport", slug="sport")
    assert cat.is_active is True


def test_category_id_is_int_or_none():
    cat_no_id = Category(name="A", slug="a")
    assert cat_no_id.id is None

    cat_with_id = Category(name="B", slug="b", id=42)
    assert cat_with_id.id == 42


def test_category_protocol_exists():
    """CategoryRepositoryInterface must be importable as a Protocol."""
    from app.domain.category.repository import CategoryRepositoryInterface

    assert CategoryRepositoryInterface is not None


def test_category_repository_protocol_has_required_methods():
    """Protocol must define all required method names."""
    from app.domain.category.repository import CategoryRepositoryInterface

    required = [
        "create",
        "get_by_id",
        "get_by_slug",
        "get_by_slug_active",
        "list_active",
        "list_all",
        "update",
        "set_inactive",
    ]
    for method in required:
        assert hasattr(CategoryRepositoryInterface, method), (
            f"Missing method: {method}"
        )
