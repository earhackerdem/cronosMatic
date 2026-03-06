"""API integration tests for public and admin category endpoints."""

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.db.base import Base
from app.db.engine import get_db_session
from app.main import app


# ─── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
async def cat_client():
    """HTTP client with per-test DB session, truncating categories + auth tables."""
    from httpx import ASGITransport, AsyncClient

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
                "TRUNCATE TABLE categories, refresh_tokens, users RESTART IDENTITY CASCADE"
            )
        )

    await engine.dispose()


@pytest.fixture
async def admin_token(cat_client):
    """Register an admin user and return a bearer token."""
    # Register normal user
    resp = await cat_client.post(
        "/api/v1/auth/register",
        json={
            "name": "Admin User",
            "email": "admin@categories.example.com",
            "password": "password123",
            "password_confirmation": "password123",
        },
    )
    assert resp.status_code == 201, resp.text
    token = resp.json()["access_token"]

    # Promote to admin via DB
    from sqlalchemy import update
    from app.models.user import UserModel

    engine = create_async_engine(settings.database_url, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        await session.execute(
            update(UserModel)
            .where(UserModel.email == "admin@categories.example.com")
            .values(is_admin=True)
        )
        await session.commit()
    await engine.dispose()

    # Re-login to get a token reflecting admin status (or just use the same token)
    # The token carries user ID; require_admin checks DB user.is_admin live.
    # The existing token still works since is_admin is checked from DB on each request.
    return token


@pytest.fixture
async def user_token(cat_client):
    """Register a non-admin user and return a bearer token."""
    resp = await cat_client.post(
        "/api/v1/auth/register",
        json={
            "name": "Normal User",
            "email": "user@categories.example.com",
            "password": "password123",
            "password_confirmation": "password123",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["access_token"]


async def _create_category_via_admin(client, token, **kwargs) -> dict:
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


# ─── Public: GET /categories ─────────────────────────────────────────────────


async def test_list_active_categories_returns_200(cat_client):
    resp = await cat_client.get("/api/v1/categories")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "pages" in data
    assert "size" in data


async def test_list_active_categories_default_page_size_is_10(cat_client):
    resp = await cat_client.get("/api/v1/categories")
    assert resp.status_code == 200
    assert resp.json()["size"] == 10


async def test_list_active_categories_excludes_inactive(cat_client, admin_token):
    await _create_category_via_admin(
        cat_client, admin_token, name="Active", slug="active-pub", is_active=True
    )
    await _create_category_via_admin(
        cat_client, admin_token, name="Inactive", slug="inactive-pub", is_active=False
    )

    resp = await cat_client.get("/api/v1/categories")
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["slug"] == "active-pub"


async def test_list_active_categories_custom_page_and_size(cat_client, admin_token):
    for i in range(6):
        await _create_category_via_admin(
            cat_client, admin_token, name=f"Cat {i}", slug=f"cat-page-{i}"
        )

    resp = await cat_client.get("/api/v1/categories?page=2&size=5")
    data = resp.json()
    assert data["page"] == 2
    assert data["size"] == 5
    assert data["total"] == 6
    assert len(data["items"]) == 1  # page 2 with size 5, 6 total => 1 on page 2


# ─── Public: GET /categories/{slug} ─────────────────────────────────────────


async def test_get_category_by_slug_returns_200_with_products_stub(
    cat_client, admin_token
):
    await _create_category_via_admin(
        cat_client, admin_token, name="Pocket", slug="pocket"
    )
    resp = await cat_client.get("/api/v1/categories/pocket")
    assert resp.status_code == 200
    data = resp.json()
    assert "category" in data
    assert "products" in data
    assert data["products"]["total"] == 0
    assert data["products"]["items"] == []


async def test_get_category_by_slug_404_for_inactive(cat_client, admin_token):
    await _create_category_via_admin(
        cat_client, admin_token, slug="inactive-slug", is_active=False
    )
    resp = await cat_client.get("/api/v1/categories/inactive-slug")
    assert resp.status_code == 404


async def test_get_category_by_slug_404_for_missing_slug(cat_client):
    resp = await cat_client.get("/api/v1/categories/does-not-exist")
    assert resp.status_code == 404


async def test_get_category_by_slug_image_url_null_when_no_image_path(
    cat_client, admin_token
):
    await _create_category_via_admin(
        cat_client, admin_token, slug="no-img", image_path=None
    )
    resp = await cat_client.get("/api/v1/categories/no-img")
    assert resp.status_code == 200
    assert resp.json()["category"]["image_url"] is None


async def test_get_category_by_slug_image_url_passthrough_when_http(
    cat_client, admin_token
):
    await _create_category_via_admin(
        cat_client,
        admin_token,
        slug="http-img",
        image_path="https://cdn.example.com/img.jpg",
    )
    resp = await cat_client.get("/api/v1/categories/http-img")
    assert resp.status_code == 200
    assert (
        resp.json()["category"]["image_url"] == "https://cdn.example.com/img.jpg"
    )


async def test_get_category_by_slug_image_url_prepends_storage_base_url(
    cat_client, admin_token, monkeypatch
):
    monkeypatch.setattr(settings, "storage_base_url", "https://storage.example.com")
    await _create_category_via_admin(
        cat_client, admin_token, slug="rel-img", image_path="categories/img.jpg"
    )
    resp = await cat_client.get("/api/v1/categories/rel-img")
    assert resp.status_code == 200
    assert (
        resp.json()["category"]["image_url"]
        == "https://storage.example.com/categories/img.jpg"
    )


# ─── Admin: GET /admin/categories ────────────────────────────────────────────


async def test_admin_list_all_categories_returns_200(cat_client, admin_token):
    await _create_category_via_admin(
        cat_client, admin_token, slug="admin-list-1", is_active=True
    )
    await _create_category_via_admin(
        cat_client, admin_token, slug="admin-list-2", is_active=False
    )

    resp = await cat_client.get(
        "/api/v1/admin/categories",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2


async def test_admin_list_all_categories_default_size_is_15(cat_client, admin_token):
    resp = await cat_client.get(
        "/api/v1/admin/categories",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["size"] == 15


async def test_admin_list_categories_returns_403_for_non_admin(
    cat_client, user_token
):
    resp = await cat_client.get(
        "/api/v1/admin/categories",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 403


async def test_admin_list_categories_returns_401_without_token(cat_client):
    resp = await cat_client.get("/api/v1/admin/categories")
    assert resp.status_code == 401


# ─── Admin: POST /admin/categories ───────────────────────────────────────────


async def test_admin_create_category_returns_201(cat_client, admin_token):
    resp = await cat_client.post(
        "/api/v1/admin/categories",
        json={"name": "New Cat", "slug": "new-cat"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "New Cat"
    assert data["slug"] == "new-cat"
    assert data["id"] is not None
    assert "created_at" in data
    assert "updated_at" in data


async def test_admin_create_category_409_on_duplicate_slug(cat_client, admin_token):
    await _create_category_via_admin(cat_client, admin_token, slug="dup-slug")

    resp = await cat_client.post(
        "/api/v1/admin/categories",
        json={"name": "Dup", "slug": "dup-slug"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 409


async def test_admin_create_category_422_missing_required_fields(
    cat_client, admin_token
):
    resp = await cat_client.post(
        "/api/v1/admin/categories",
        json={"slug": "no-name"},  # missing name
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 422


# ─── Admin: GET /admin/categories/{id} ───────────────────────────────────────


async def test_admin_get_category_by_id_returns_200(cat_client, admin_token):
    created = await _create_category_via_admin(
        cat_client, admin_token, slug="get-by-id"
    )
    cat_id = created["id"]

    resp = await cat_client.get(
        f"/api/v1/admin/categories/{cat_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == cat_id


async def test_admin_get_category_by_id_404_not_found(cat_client, admin_token):
    resp = await cat_client.get(
        "/api/v1/admin/categories/99999",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404


# ─── Admin: PUT /admin/categories/{id} ───────────────────────────────────────


async def test_admin_update_category_returns_200(cat_client, admin_token):
    created = await _create_category_via_admin(
        cat_client, admin_token, name="Before", slug="before-update"
    )
    cat_id = created["id"]

    resp = await cat_client.put(
        f"/api/v1/admin/categories/{cat_id}",
        json={"name": "After"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "After"
    assert resp.json()["slug"] == "before-update"  # unchanged


async def test_admin_update_category_409_on_slug_collision(cat_client, admin_token):
    await _create_category_via_admin(cat_client, admin_token, slug="slug-a")
    cat_b = await _create_category_via_admin(cat_client, admin_token, slug="slug-b")

    resp = await cat_client.put(
        f"/api/v1/admin/categories/{cat_b['id']}",
        json={"slug": "slug-a"},  # taken by cat_a
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 409


async def test_admin_update_category_404_not_found(cat_client, admin_token):
    resp = await cat_client.put(
        "/api/v1/admin/categories/99999",
        json={"name": "Whatever"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404


# ─── Admin: DELETE /admin/categories/{id} ────────────────────────────────────


async def test_admin_delete_category_returns_204(cat_client, admin_token):
    created = await _create_category_via_admin(
        cat_client, admin_token, slug="to-delete"
    )
    cat_id = created["id"]

    resp = await cat_client.delete(
        f"/api/v1/admin/categories/{cat_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 204


async def test_admin_delete_category_returns_404_not_found(cat_client, admin_token):
    resp = await cat_client.delete(
        "/api/v1/admin/categories/99999",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404


async def test_admin_delete_sets_is_active_false_not_removes_record(
    cat_client, admin_token
):
    created = await _create_category_via_admin(
        cat_client, admin_token, slug="soft-delete"
    )
    cat_id = created["id"]

    # Delete (soft)
    del_resp = await cat_client.delete(
        f"/api/v1/admin/categories/{cat_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert del_resp.status_code == 204

    # Admin GET by ID still returns the record
    get_resp = await cat_client.get(
        f"/api/v1/admin/categories/{cat_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["is_active"] is False
