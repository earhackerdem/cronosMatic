"""API integration tests for cart endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.db.base import Base
from app.db.engine import get_db_session
from app.main import app
from app.models.cart import CartItemModel, CartModel  # noqa: F401
from app.models.user import UserModel


# ─── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
async def cart_client():
    """HTTP client with per-test DB session. Truncates all tables after each test."""
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
                "TRUNCATE TABLE cart_items, carts, products, categories, refresh_tokens, users RESTART IDENTITY CASCADE"
            )
        )

    await engine.dispose()


@pytest.fixture
async def user_token(cart_client):
    """Register a normal user and return their bearer token."""
    resp = await cart_client.post(
        "/api/v1/auth/register",
        json={
            "name": "Cart User",
            "email": "cartuser@example.com",
            "password": "password123",
            "password_confirmation": "password123",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["access_token"]


@pytest.fixture
async def user_token_b(cart_client):
    """Register a second normal user and return their bearer token."""
    resp = await cart_client.post(
        "/api/v1/auth/register",
        json={
            "name": "Cart User B",
            "email": "cartuserb@example.com",
            "password": "password123",
            "password_confirmation": "password123",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["access_token"]


@pytest.fixture
async def admin_token(cart_client):
    """Register an admin user and return their bearer token."""
    resp = await cart_client.post(
        "/api/v1/auth/register",
        json={
            "name": "Cart Admin",
            "email": "cartadmin@example.com",
            "password": "password123",
            "password_confirmation": "password123",
        },
    )
    assert resp.status_code == 201, resp.text
    token = resp.json()["access_token"]

    engine = create_async_engine(settings.database_url, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        await session.execute(
            update(UserModel)
            .where(UserModel.email == "cartadmin@example.com")
            .values(is_admin=True)
        )
        await session.commit()
    await engine.dispose()

    return token


async def _create_category(client, token, **kwargs) -> dict:
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
    defaults = {
        "category_id": category_id,
        "name": "Test Watch",
        "sku": "SKU-CART-001",
        "price": "199.99",
        "stock_quantity": 10,
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


# ─── GET /cart ─────────────────────────────────────────────────────────────────


async def test_get_cart_authenticated_creates_empty_cart(cart_client, user_token):
    resp = await cart_client.get(
        "/api/v1/cart",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total_items"] == 0
    assert data["total_amount"] == "0.00"
    assert data["user_id"] is not None
    assert data["session_id"] is None


async def test_get_cart_guest_creates_empty_cart_with_session_id(cart_client):
    resp = await cart_client.get(
        "/api/v1/cart",
        headers={"X-Session-ID": "guest-session-abc123"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == "guest-session-abc123"
    assert data["expires_at"] is not None
    assert data["items"] == []


async def test_get_cart_400_no_auth_and_no_session_id(cart_client):
    resp = await cart_client.get("/api/v1/cart")
    assert resp.status_code == 400


async def test_get_cart_returns_existing_cart_on_second_request(
    cart_client, user_token
):
    resp1 = await cart_client.get(
        "/api/v1/cart",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    resp2 = await cart_client.get(
        "/api/v1/cart",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp1.status_code == 200
    assert resp2.status_code == 200
    assert resp1.json()["id"] == resp2.json()["id"]


# ─── POST /cart/items ─────────────────────────────────────────────────────────


async def test_add_item_returns_201_with_updated_cart(
    cart_client, user_token, admin_token
):
    cat = await _create_category(cart_client, admin_token, slug="add-item-cat")
    product = await _create_product(
        cart_client, admin_token, cat["id"], slug="add-item-watch", sku="AI-001"
    )

    resp = await cart_client.post(
        "/api/v1/cart/items",
        json={"product_id": product["id"], "quantity": 2},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["product_id"] == product["id"]
    assert data["items"][0]["quantity"] == 2


async def test_add_item_increments_quantity_when_product_exists(
    cart_client, user_token, admin_token
):
    cat = await _create_category(cart_client, admin_token, slug="increment-cat")
    product = await _create_product(
        cart_client,
        admin_token,
        cat["id"],
        slug="increment-watch",
        sku="INC-001",
        stock_quantity=20,
    )

    headers = {"Authorization": f"Bearer {user_token}"}
    await cart_client.post(
        "/api/v1/cart/items",
        json={"product_id": product["id"], "quantity": 3},
        headers=headers,
    )
    resp = await cart_client.post(
        "/api/v1/cart/items",
        json={"product_id": product["id"], "quantity": 4},
        headers=headers,
    )
    assert resp.status_code == 201
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["quantity"] == 7


async def test_add_item_422_product_not_found(cart_client, user_token):
    resp = await cart_client.post(
        "/api/v1/cart/items",
        json={"product_id": 999999, "quantity": 1},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 422


async def test_add_item_422_inactive_product(cart_client, user_token, admin_token):
    cat = await _create_category(cart_client, admin_token, slug="inactive-p-cat")
    product = await _create_product(
        cart_client,
        admin_token,
        cat["id"],
        slug="inactive-p-watch",
        sku="INACT-P-001",
        is_active=False,
    )

    resp = await cart_client.post(
        "/api/v1/cart/items",
        json={"product_id": product["id"], "quantity": 1},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 422
    assert "not available" in resp.json()["detail"]


async def test_add_item_422_insufficient_stock(cart_client, user_token, admin_token):
    cat = await _create_category(cart_client, admin_token, slug="stock-cat")
    product = await _create_product(
        cart_client,
        admin_token,
        cat["id"],
        slug="low-stock-watch",
        sku="LS-001",
        stock_quantity=5,
    )

    resp = await cart_client.post(
        "/api/v1/cart/items",
        json={"product_id": product["id"], "quantity": 10},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 422
    assert "stock" in resp.json()["detail"].lower()


async def test_add_item_422_quantity_zero(cart_client, user_token):
    resp = await cart_client.post(
        "/api/v1/cart/items",
        json={"product_id": 1, "quantity": 0},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 422


async def test_add_item_422_stock_exceeded_on_increment(
    cart_client, user_token, admin_token
):
    cat = await _create_category(cart_client, admin_token, slug="inc-stock-cat")
    product = await _create_product(
        cart_client,
        admin_token,
        cat["id"],
        slug="inc-stock-watch",
        sku="IS-001",
        stock_quantity=5,
    )

    headers = {"Authorization": f"Bearer {user_token}"}
    await cart_client.post(
        "/api/v1/cart/items",
        json={"product_id": product["id"], "quantity": 4},
        headers=headers,
    )
    resp = await cart_client.post(
        "/api/v1/cart/items",
        json={"product_id": product["id"], "quantity": 3},
        headers=headers,
    )
    assert resp.status_code == 422


async def test_add_item_response_contains_nested_product(
    cart_client, user_token, admin_token
):
    cat = await _create_category(cart_client, admin_token, slug="nested-p-cat")
    product = await _create_product(
        cart_client,
        admin_token,
        cat["id"],
        slug="nested-p-watch",
        sku="NP-001",
        price="250.00",
    )

    resp = await cart_client.post(
        "/api/v1/cart/items",
        json={"product_id": product["id"], "quantity": 1},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 201
    item = resp.json()["items"][0]
    assert item["product"]["id"] == product["id"]
    assert item["product"]["name"] == product["name"]
    assert item["product"]["price"] == "250.00"


# ─── PUT /cart/items/{cart_item_id} ──────────────────────────────────────────


async def test_update_item_returns_200_with_recalculated_total(
    cart_client, user_token, admin_token
):
    cat = await _create_category(cart_client, admin_token, slug="upd-item-cat")
    product = await _create_product(
        cart_client,
        admin_token,
        cat["id"],
        slug="upd-item-watch",
        sku="UI-001",
        price="100.00",
        stock_quantity=20,
    )

    headers = {"Authorization": f"Bearer {user_token}"}
    add_resp = await cart_client.post(
        "/api/v1/cart/items",
        json={"product_id": product["id"], "quantity": 1},
        headers=headers,
    )
    item_id = add_resp.json()["items"][0]["id"]

    resp = await cart_client.put(
        f"/api/v1/cart/items/{item_id}",
        json={"quantity": 5},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    item = next(i for i in data["items"] if i["id"] == item_id)
    assert item["quantity"] == 5
    assert item["total_price"] == "500.00"
    assert data["total_items"] == 5


async def test_update_item_422_insufficient_stock(cart_client, user_token, admin_token):
    cat = await _create_category(cart_client, admin_token, slug="upd-stock-cat")
    product = await _create_product(
        cart_client,
        admin_token,
        cat["id"],
        slug="upd-stock-watch",
        sku="US-001",
        stock_quantity=3,
    )

    headers = {"Authorization": f"Bearer {user_token}"}
    add_resp = await cart_client.post(
        "/api/v1/cart/items",
        json={"product_id": product["id"], "quantity": 1},
        headers=headers,
    )
    item_id = add_resp.json()["items"][0]["id"]

    resp = await cart_client.put(
        f"/api/v1/cart/items/{item_id}",
        json={"quantity": 100},
        headers=headers,
    )
    assert resp.status_code == 422


async def test_update_item_404_item_not_found(cart_client, user_token):
    resp = await cart_client.put(
        "/api/v1/cart/items/99999",
        json={"quantity": 1},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 404


async def test_update_item_403_item_belongs_to_other_user(
    cart_client, user_token, user_token_b, admin_token
):
    cat = await _create_category(cart_client, admin_token, slug="ownership-cat")
    product = await _create_product(
        cart_client,
        admin_token,
        cat["id"],
        slug="ownership-watch",
        sku="OW-001",
    )

    # User A adds item
    add_resp = await cart_client.post(
        "/api/v1/cart/items",
        json={"product_id": product["id"], "quantity": 1},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    item_id = add_resp.json()["items"][0]["id"]

    # User B tries to update it
    resp = await cart_client.put(
        f"/api/v1/cart/items/{item_id}",
        json={"quantity": 2},
        headers={"Authorization": f"Bearer {user_token_b}"},
    )
    assert resp.status_code == 403


# ─── DELETE /cart/items/{cart_item_id} ───────────────────────────────────────


async def test_delete_item_returns_200_with_cart(cart_client, user_token, admin_token):
    cat = await _create_category(cart_client, admin_token, slug="del-item-cat")
    product = await _create_product(
        cart_client, admin_token, cat["id"], slug="del-item-watch", sku="DI-001"
    )

    headers = {"Authorization": f"Bearer {user_token}"}
    add_resp = await cart_client.post(
        "/api/v1/cart/items",
        json={"product_id": product["id"], "quantity": 1},
        headers=headers,
    )
    item_id = add_resp.json()["items"][0]["id"]

    resp = await cart_client.delete(
        f"/api/v1/cart/items/{item_id}",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert all(i["id"] != item_id for i in data["items"])


async def test_delete_item_403_item_belongs_to_other_user(
    cart_client, user_token, user_token_b, admin_token
):
    cat = await _create_category(cart_client, admin_token, slug="del-own-cat")
    product = await _create_product(
        cart_client, admin_token, cat["id"], slug="del-own-watch", sku="DO-001"
    )

    add_resp = await cart_client.post(
        "/api/v1/cart/items",
        json={"product_id": product["id"], "quantity": 1},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    item_id = add_resp.json()["items"][0]["id"]

    resp = await cart_client.delete(
        f"/api/v1/cart/items/{item_id}",
        headers={"Authorization": f"Bearer {user_token_b}"},
    )
    assert resp.status_code == 403


async def test_delete_item_404_item_not_found(cart_client, user_token):
    resp = await cart_client.delete(
        "/api/v1/cart/items/99999",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 404


# ─── DELETE /cart ─────────────────────────────────────────────────────────────


async def test_clear_cart_returns_200_empty_cart(cart_client, user_token, admin_token):
    cat = await _create_category(cart_client, admin_token, slug="clear-cat")
    product = await _create_product(
        cart_client, admin_token, cat["id"], slug="clear-watch", sku="CL-001"
    )

    headers = {"Authorization": f"Bearer {user_token}"}
    await cart_client.post(
        "/api/v1/cart/items",
        json={"product_id": product["id"], "quantity": 2},
        headers=headers,
    )

    resp = await cart_client.delete("/api/v1/cart", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total_items"] == 0
    assert data["total_amount"] == "0.00"


async def test_clear_cart_guest(cart_client, admin_token):
    cat = await _create_category(cart_client, admin_token, slug="guest-clear-cat")
    product = await _create_product(
        cart_client, admin_token, cat["id"], slug="guest-clear-watch", sku="GC-001"
    )

    session_headers = {"X-Session-ID": "guest-clear-session"}
    await cart_client.post(
        "/api/v1/cart/items",
        json={"product_id": product["id"], "quantity": 1},
        headers=session_headers,
    )

    resp = await cart_client.delete("/api/v1/cart", headers=session_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total_items"] == 0


# ─── Totals ──────────────────────────────────────────────────────────────────


async def test_cart_totals_recalculate_after_add(cart_client, user_token, admin_token):
    cat = await _create_category(cart_client, admin_token, slug="totals-cat")
    prod1 = await _create_product(
        cart_client,
        admin_token,
        cat["id"],
        slug="totals-w1",
        sku="T1-001",
        price="10.00",
        stock_quantity=10,
    )
    prod2 = await _create_product(
        cart_client,
        admin_token,
        cat["id"],
        name="Watch 2",
        slug="totals-w2",
        sku="T2-001",
        price="20.00",
        stock_quantity=10,
    )

    headers = {"Authorization": f"Bearer {user_token}"}
    await cart_client.post(
        "/api/v1/cart/items",
        json={"product_id": prod1["id"], "quantity": 2},
        headers=headers,
    )
    resp = await cart_client.post(
        "/api/v1/cart/items",
        json={"product_id": prod2["id"], "quantity": 3},
        headers=headers,
    )

    data = resp.json()
    # 2 distinct products, 2+3=5 total items, 2*10 + 3*20 = 80
    assert data["total_items"] == 5
    assert data["total_amount"] == "80.00"


async def test_cart_totals_recalculate_after_remove(
    cart_client, user_token, admin_token
):
    cat = await _create_category(cart_client, admin_token, slug="rm-totals-cat")
    product = await _create_product(
        cart_client,
        admin_token,
        cat["id"],
        slug="rm-totals-watch",
        sku="RT-001",
    )

    headers = {"Authorization": f"Bearer {user_token}"}
    add_resp = await cart_client.post(
        "/api/v1/cart/items",
        json={"product_id": product["id"], "quantity": 3},
        headers=headers,
    )
    item_id = add_resp.json()["items"][0]["id"]

    resp = await cart_client.delete(
        f"/api/v1/cart/items/{item_id}",
        headers=headers,
    )
    data = resp.json()
    assert data["total_items"] == 0
    assert data["total_amount"] == "0.00"


async def test_cart_summary_subtotal_matches_total_amount(
    cart_client, user_token, admin_token
):
    cat = await _create_category(cart_client, admin_token, slug="summary-cat")
    product = await _create_product(
        cart_client,
        admin_token,
        cat["id"],
        slug="summary-watch",
        sku="SM-001",
        price="50.00",
        stock_quantity=10,
    )

    resp = await cart_client.post(
        "/api/v1/cart/items",
        json={"product_id": product["id"], "quantity": 3},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    data = resp.json()
    assert data["summary"]["subtotal"] == data["total_amount"]
    assert data["summary"]["total_items"] == data["total_items"]


# ─── POST /cart/merge ─────────────────────────────────────────────────────────


async def test_merge_cart_returns_200(cart_client, user_token, admin_token):
    cat = await _create_category(cart_client, admin_token, slug="merge-cat")
    product = await _create_product(
        cart_client, admin_token, cat["id"], slug="merge-watch", sku="MG-001"
    )

    # Guest adds product
    guest_session = "merge-guest-session-001"
    await cart_client.post(
        "/api/v1/cart/items",
        json={"product_id": product["id"], "quantity": 2},
        headers={"X-Session-ID": guest_session},
    )

    # User merges
    resp = await cart_client.post(
        "/api/v1/cart/merge",
        json={"session_id": guest_session},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["product_id"] == product["id"]
    assert data["items"][0]["quantity"] == 2


async def test_merge_cart_sums_quantity_for_existing_product(
    cart_client, user_token, admin_token
):
    cat = await _create_category(cart_client, admin_token, slug="merge-sum-cat")
    product = await _create_product(
        cart_client,
        admin_token,
        cat["id"],
        slug="merge-sum-watch",
        sku="MS-001",
        stock_quantity=20,
    )

    headers_user = {"Authorization": f"Bearer {user_token}"}
    guest_session = "merge-sum-session"

    # User adds 3
    await cart_client.post(
        "/api/v1/cart/items",
        json={"product_id": product["id"], "quantity": 3},
        headers=headers_user,
    )
    # Guest adds 4
    await cart_client.post(
        "/api/v1/cart/items",
        json={"product_id": product["id"], "quantity": 4},
        headers={"X-Session-ID": guest_session},
    )

    resp = await cart_client.post(
        "/api/v1/cart/merge",
        json={"session_id": guest_session},
        headers=headers_user,
    )
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["quantity"] == 7


async def test_merge_cart_silently_discards_when_stock_insufficient(
    cart_client, user_token, admin_token
):
    cat = await _create_category(cart_client, admin_token, slug="merge-disc-cat")
    product = await _create_product(
        cart_client,
        admin_token,
        cat["id"],
        slug="merge-disc-watch",
        sku="MD-001",
        stock_quantity=5,
    )

    headers_user = {"Authorization": f"Bearer {user_token}"}
    guest_session = "merge-discard-session"

    # User already has 4 in cart
    await cart_client.post(
        "/api/v1/cart/items",
        json={"product_id": product["id"], "quantity": 4},
        headers=headers_user,
    )
    # Guest has 3 more — total would be 7 but stock is only 5 → discard
    await cart_client.post(
        "/api/v1/cart/items",
        json={"product_id": product["id"], "quantity": 3},
        headers={"X-Session-ID": guest_session},
    )

    resp = await cart_client.post(
        "/api/v1/cart/merge",
        json={"session_id": guest_session},
        headers=headers_user,
    )
    assert resp.status_code == 200
    items = resp.json()["items"]
    # Should still have user's original 4 (guest item discarded)
    assert len(items) == 1
    assert items[0]["quantity"] == 4


async def test_merge_cart_deletes_guest_cart_after_merge(
    cart_client, user_token, admin_token
):
    cat = await _create_category(cart_client, admin_token, slug="merge-del-cat")
    product = await _create_product(
        cart_client, admin_token, cat["id"], slug="merge-del-watch", sku="MDL-001"
    )

    guest_session = "merge-delete-session"
    await cart_client.post(
        "/api/v1/cart/items",
        json={"product_id": product["id"], "quantity": 1},
        headers={"X-Session-ID": guest_session},
    )

    # Merge into user cart
    await cart_client.post(
        "/api/v1/cart/merge",
        json={"session_id": guest_session},
        headers={"Authorization": f"Bearer {user_token}"},
    )

    # Guest cart should be gone — GET returns fresh empty cart
    resp = await cart_client.get(
        "/api/v1/cart",
        headers={"X-Session-ID": guest_session},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["session_id"] == guest_session


async def test_merge_cart_returns_user_cart_unchanged_when_no_guest_cart(
    cart_client, user_token
):
    resp = await cart_client.post(
        "/api/v1/cart/merge",
        json={"session_id": "nonexistent-session-xyz"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []


async def test_merge_cart_401_without_bearer_token(cart_client):
    resp = await cart_client.post(
        "/api/v1/cart/merge",
        json={"session_id": "some-session"},
        headers={"X-Session-ID": "some-session"},
    )
    assert resp.status_code == 401
