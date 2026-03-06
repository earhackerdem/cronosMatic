"""API integration tests for public and admin product endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.db.base import Base
from app.db.engine import get_db_session
from app.main import app
from app.models.user import UserModel


# ─── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
async def prod_client():
    """HTTP client with per-test DB session, truncating products + categories + auth tables."""
    engine = create_async_engine(settings.database_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()

    async with engine.begin() as conn:
        await conn.execute(
            text(
                "TRUNCATE TABLE products, categories, refresh_tokens, users RESTART IDENTITY CASCADE"
            )
        )

    await engine.dispose()


@pytest.fixture
async def admin_token(prod_client):
    """Register an admin user and return a bearer token."""
    resp = await prod_client.post(
        "/api/v1/auth/register",
        json={
            "name": "Admin User",
            "email": "admin@products.example.com",
            "password": "password123",
            "password_confirmation": "password123",
        },
    )
    assert resp.status_code == 201, resp.text
    token = resp.json()["access_token"]

    # Promote to admin via DB
    engine = create_async_engine(settings.database_url, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        await session.execute(
            update(UserModel)
            .where(UserModel.email == "admin@products.example.com")
            .values(is_admin=True)
        )
        await session.commit()
    await engine.dispose()

    return token


@pytest.fixture
async def user_token(prod_client):
    """Register a non-admin user and return a bearer token."""
    resp = await prod_client.post(
        "/api/v1/auth/register",
        json={
            "name": "Normal User",
            "email": "user@products.example.com",
            "password": "password123",
            "password_confirmation": "password123",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["access_token"]


async def _create_category(client, token, **kwargs) -> dict:
    """Helper to create a category via admin API."""
    defaults = {"name": "Test Cat", "slug": "test-cat", "is_active": True}
    defaults.update(kwargs)
    resp = await client.post(
        "/api/v1/admin/categories",
        json=defaults,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _create_product(client, token, category_id: int, **kwargs) -> dict:
    """Helper to create a product via admin API."""
    defaults = {
        "category_id": category_id,
        "name": "Test Watch",
        "sku": "SKU-TEST-001",
        "price": "199.99",
        "is_active": True,
    }
    defaults.update(kwargs)
    resp = await client.post(
        "/api/v1/admin/products",
        json=defaults,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# ─── Public: GET /products ────────────────────────────────────────────────────


async def test_list_products_returns_200(prod_client):
    resp = await prod_client.get("/api/v1/products")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "pages" in data
    assert "size" in data


async def test_list_products_default_size_is_12(prod_client):
    resp = await prod_client.get("/api/v1/products")
    assert resp.status_code == 200
    assert resp.json()["size"] == 12


async def test_list_products_excludes_inactive(prod_client, admin_token):
    cat = await _create_category(prod_client, admin_token, slug="cat-for-active")
    await _create_product(prod_client, admin_token, cat["id"], slug="active-prod", sku="ACT-1", is_active=True)
    await _create_product(prod_client, admin_token, cat["id"], name="Inactive", slug="inactive-prod", sku="INACT-1", is_active=False)

    resp = await prod_client.get("/api/v1/products")
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["slug"] == "active-prod"


async def test_list_products_filter_by_category_slug(prod_client, admin_token):
    cat1 = await _create_category(prod_client, admin_token, name="Cat A", slug="cat-a")
    cat2 = await _create_category(prod_client, admin_token, name="Cat B", slug="cat-b")
    await _create_product(prod_client, admin_token, cat1["id"], slug="prod-a", sku="SKU-A")
    await _create_product(prod_client, admin_token, cat2["id"], slug="prod-b", sku="SKU-B")

    resp = await prod_client.get("/api/v1/products?category=cat-a")
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["slug"] == "prod-a"


async def test_list_products_404_for_invalid_category(prod_client):
    resp = await prod_client.get("/api/v1/products?category=nonexistent-cat")
    assert resp.status_code == 404


async def test_list_products_search_by_name(prod_client, admin_token):
    cat = await _create_category(prod_client, admin_token, slug="search-cat")
    await _create_product(prod_client, admin_token, cat["id"], name="Rolex Submariner", slug="rolex-sub", sku="RS-001")
    await _create_product(prod_client, admin_token, cat["id"], name="Omega Speedmaster", slug="omega-speed", sku="OS-001")

    resp = await prod_client.get("/api/v1/products?search=rolex")
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "Rolex Submariner"


async def test_list_products_nested_category_in_response(prod_client, admin_token):
    cat = await _create_category(prod_client, admin_token, name="Dive Watches", slug="dive-watches")
    await _create_product(prod_client, admin_token, cat["id"], slug="dive-watch", sku="DW-001")

    resp = await prod_client.get("/api/v1/products")
    data = resp.json()
    assert data["total"] == 1
    item = data["items"][0]
    assert "category" in item
    assert item["category"]["slug"] == "dive-watches"
    assert item["category"]["name"] == "Dive Watches"


async def test_list_products_custom_pagination(prod_client, admin_token):
    cat = await _create_category(prod_client, admin_token, slug="pg-cat")
    for i in range(7):
        await _create_product(prod_client, admin_token, cat["id"], slug=f"pg-prod-{i}", sku=f"PG-{i}")

    resp = await prod_client.get("/api/v1/products?page=2&size=5")
    data = resp.json()
    assert data["page"] == 2
    assert data["size"] == 5
    assert data["total"] == 7
    assert len(data["items"]) == 2


async def test_list_products_sort_by_price_desc(prod_client, admin_token):
    cat = await _create_category(prod_client, admin_token, slug="sort-cat")
    await _create_product(prod_client, admin_token, cat["id"], slug="cheap-w", sku="CH-1", price="100.00")
    await _create_product(prod_client, admin_token, cat["id"], slug="exp-w", sku="EX-1", price="9999.00")

    resp = await prod_client.get("/api/v1/products?sort_by=price&sort_direction=desc")
    data = resp.json()
    assert data["items"][0]["price"] == "9999.00"
    assert data["items"][1]["price"] == "100.00"


# ─── Public: GET /products/{slug} ────────────────────────────────────────────


async def test_get_product_by_slug_returns_200(prod_client, admin_token):
    cat = await _create_category(prod_client, admin_token, slug="detail-cat")
    await _create_product(prod_client, admin_token, cat["id"], slug="detail-watch", sku="DT-001")

    resp = await prod_client.get("/api/v1/products/detail-watch")
    assert resp.status_code == 200
    data = resp.json()
    assert data["slug"] == "detail-watch"
    assert "category" in data
    assert data["category"]["slug"] == "detail-cat"


async def test_get_product_by_slug_404_for_inactive(prod_client, admin_token):
    cat = await _create_category(prod_client, admin_token, slug="inactive-cat")
    await _create_product(prod_client, admin_token, cat["id"], slug="inactive-watch", sku="IW-001", is_active=False)

    resp = await prod_client.get("/api/v1/products/inactive-watch")
    assert resp.status_code == 404


async def test_get_product_by_slug_404_for_missing(prod_client):
    resp = await prod_client.get("/api/v1/products/does-not-exist")
    assert resp.status_code == 404


async def test_get_product_image_url_null_when_no_image_path(prod_client, admin_token):
    cat = await _create_category(prod_client, admin_token, slug="img-cat")
    await _create_product(prod_client, admin_token, cat["id"], slug="no-img-watch", sku="NI-001")

    resp = await prod_client.get("/api/v1/products/no-img-watch")
    assert resp.status_code == 200
    assert resp.json()["image_url"] is None


async def test_get_product_image_url_passthrough_when_http(prod_client, admin_token):
    cat = await _create_category(prod_client, admin_token, slug="http-cat")
    await _create_product(
        prod_client, admin_token, cat["id"],
        slug="http-img-watch", sku="HI-001",
        image_path="https://cdn.example.com/watch.jpg"
    )

    resp = await prod_client.get("/api/v1/products/http-img-watch")
    assert resp.status_code == 200
    assert resp.json()["image_url"] == "https://cdn.example.com/watch.jpg"


# ─── Admin: GET /admin/products ───────────────────────────────────────────────


async def test_admin_list_products_returns_200(prod_client, admin_token):
    cat = await _create_category(prod_client, admin_token, slug="admin-list-cat")
    await _create_product(prod_client, admin_token, cat["id"], slug="a-prod-1", sku="AP-1", is_active=True)
    await _create_product(prod_client, admin_token, cat["id"], slug="a-prod-2", sku="AP-2", is_active=False)

    resp = await prod_client.get(
        "/api/v1/admin/products",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == 2


async def test_admin_list_products_default_size_is_15(prod_client, admin_token):
    resp = await prod_client.get(
        "/api/v1/admin/products",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["size"] == 15


async def test_admin_list_products_401_without_token(prod_client):
    resp = await prod_client.get("/api/v1/admin/products")
    assert resp.status_code == 401


async def test_admin_list_products_403_for_non_admin(prod_client, user_token):
    resp = await prod_client.get(
        "/api/v1/admin/products",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 403


# ─── Admin: POST /admin/products ─────────────────────────────────────────────


async def test_admin_create_product_returns_201(prod_client, admin_token):
    cat = await _create_category(prod_client, admin_token, slug="create-cat")

    resp = await prod_client.post(
        "/api/v1/admin/products",
        json={
            "category_id": cat["id"],
            "name": "New Watch",
            "sku": "NW-001",
            "price": "299.99",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "New Watch"
    assert data["id"] is not None
    assert data["slug"] == "new-watch"  # auto-generated
    assert "created_at" in data
    assert "updated_at" in data
    assert "category" in data


async def test_admin_create_product_auto_generates_slug(prod_client, admin_token):
    cat = await _create_category(prod_client, admin_token, slug="slug-gen-cat")

    resp = await prod_client.post(
        "/api/v1/admin/products",
        json={
            "category_id": cat["id"],
            "name": "TAG Heuer Carrera",
            "sku": "TH-001",
            "price": "1500.00",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["slug"] == "tag-heuer-carrera"


async def test_admin_create_product_409_duplicate_slug(prod_client, admin_token):
    cat = await _create_category(prod_client, admin_token, slug="dup-slug-cat")
    await _create_product(prod_client, admin_token, cat["id"], slug="dup-watch", sku="DS-1")

    resp = await prod_client.post(
        "/api/v1/admin/products",
        json={
            "category_id": cat["id"],
            "name": "Another",
            "slug": "dup-watch",
            "sku": "DS-2",
            "price": "100.00",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 409


async def test_admin_create_product_404_missing_category(prod_client, admin_token):
    resp = await prod_client.post(
        "/api/v1/admin/products",
        json={
            "category_id": 99999,
            "name": "Watch",
            "sku": "W-001",
            "price": "100.00",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404


async def test_admin_create_product_422_missing_required_fields(prod_client, admin_token):
    resp = await prod_client.post(
        "/api/v1/admin/products",
        json={"name": "Watch"},  # missing category_id, sku, price
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 422


# ─── Admin: GET /admin/products/{id} ─────────────────────────────────────────


async def test_admin_get_product_by_id_returns_200(prod_client, admin_token):
    cat = await _create_category(prod_client, admin_token, slug="get-id-cat")
    product = await _create_product(prod_client, admin_token, cat["id"], slug="get-id-watch", sku="GI-001")

    resp = await prod_client.get(
        f"/api/v1/admin/products/{product['id']}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == product["id"]


async def test_admin_get_product_by_id_includes_inactive(prod_client, admin_token):
    cat = await _create_category(prod_client, admin_token, slug="inactive-id-cat")
    product = await _create_product(prod_client, admin_token, cat["id"], slug="inactive-id-watch", sku="II-001", is_active=False)

    resp = await prod_client.get(
        f"/api/v1/admin/products/{product['id']}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False


async def test_admin_get_product_by_id_404_not_found(prod_client, admin_token):
    resp = await prod_client.get(
        "/api/v1/admin/products/99999",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404


# ─── Admin: PUT /admin/products/{id} ─────────────────────────────────────────


async def test_admin_update_product_returns_200(prod_client, admin_token):
    cat = await _create_category(prod_client, admin_token, slug="update-cat")
    product = await _create_product(prod_client, admin_token, cat["id"], name="Old Name", slug="old-name-watch", sku="UPD-001")

    resp = await prod_client.put(
        f"/api/v1/admin/products/{product['id']}",
        json={"name": "New Name"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "New Name"
    assert resp.json()["slug"] == "old-name-watch"  # unchanged


async def test_admin_update_product_409_slug_collision(prod_client, admin_token):
    cat = await _create_category(prod_client, admin_token, slug="collision-cat")
    await _create_product(prod_client, admin_token, cat["id"], slug="slug-a-w", sku="SA-1")
    prod_b = await _create_product(prod_client, admin_token, cat["id"], slug="slug-b-w", sku="SB-1")

    resp = await prod_client.put(
        f"/api/v1/admin/products/{prod_b['id']}",
        json={"slug": "slug-a-w"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 409


async def test_admin_update_product_404_not_found(prod_client, admin_token):
    resp = await prod_client.put(
        "/api/v1/admin/products/99999",
        json={"name": "Whatever"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404


# ─── Admin: DELETE /admin/products/{id} ──────────────────────────────────────


async def test_admin_delete_product_returns_204(prod_client, admin_token):
    cat = await _create_category(prod_client, admin_token, slug="del-cat")
    product = await _create_product(prod_client, admin_token, cat["id"], slug="to-delete-watch", sku="TD-001")

    resp = await prod_client.delete(
        f"/api/v1/admin/products/{product['id']}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 204


async def test_admin_delete_product_404_not_found(prod_client, admin_token):
    resp = await prod_client.delete(
        "/api/v1/admin/products/99999",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404


async def test_admin_delete_product_hard_deletes(prod_client, admin_token):
    cat = await _create_category(prod_client, admin_token, slug="hard-del-cat")
    product = await _create_product(prod_client, admin_token, cat["id"], slug="hard-del-watch", sku="HD-001")

    # Delete
    await prod_client.delete(
        f"/api/v1/admin/products/{product['id']}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # Confirm it's gone even from admin endpoint
    get_resp = await prod_client.get(
        f"/api/v1/admin/products/{product['id']}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert get_resp.status_code == 404
