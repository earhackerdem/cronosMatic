"""API integration tests for orders endpoints."""

import re

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.db.base import Base
from app.db.engine import get_db_session
from app.main import app
from app.models.address import AddressModel  # noqa: F401
from app.models.cart import CartItemModel, CartModel  # noqa: F401
from app.models.category import CategoryModel  # noqa: F401
from app.models.order import OrderItemModel, OrderModel  # noqa: F401
from app.models.product import ProductModel  # noqa: F401
from app.models.refresh_token import RefreshTokenModel  # noqa: F401
from app.models.user import UserModel  # noqa: F401


# ─── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
async def order_client():
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
                "TRUNCATE TABLE order_items, orders, addresses, cart_items, carts, products, categories, refresh_tokens, users RESTART IDENTITY CASCADE"
            )
        )

    await engine.dispose()


# ─── Helper functions ─────────────────────────────────────────────────────────


async def _register(client: AsyncClient, email: str, name: str = "Test User") -> str:
    """Register a user and return their access token."""
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "name": name,
            "email": email,
            "password": "password123",
            "password_confirmation": "password123",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["access_token"]


async def _login(client: AsyncClient, email: str) -> str:
    """Login and return a fresh access token."""
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "password123"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


async def _register_admin(client: AsyncClient, email: str, name: str = "Admin") -> str:
    """Register user, make admin via SQL, re-login for fresh admin token."""
    await _register(client, email, name)
    await _make_admin(client, email)
    return await _login(client, email)


async def _create_category(
    client: AsyncClient, admin_token: str, slug: str = "watches"
) -> dict:
    resp = await client.post(
        "/api/v1/admin/categories",
        json={"name": "Watches", "slug": slug, "description": "Fine watches"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _make_admin(client: AsyncClient, email: str) -> None:
    """Make a user admin via direct SQL (uses a separate engine)."""
    engine = create_async_engine(settings.database_url, echo=False)
    async with engine.begin() as conn:
        await conn.execute(
            text("UPDATE users SET is_admin=true WHERE email=:email"),
            {"email": email},
        )
    await engine.dispose()


async def _create_product(
    client: AsyncClient,
    admin_token: str,
    category_id: int,
    name: str = "Test Watch",
    price: float = 99.99,
    stock: int = 10,
    sku: str = "SKU-001",
) -> dict:
    resp = await client.post(
        "/api/v1/admin/products",
        json={
            "name": name,
            "slug": name.lower().replace(" ", "-"),
            "sku": sku,
            "price": price,
            "stock_quantity": stock,
            "category_id": category_id,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _create_address(
    client: AsyncClient, token: str, addr_type: str = "shipping"
) -> dict:
    resp = await client.post(
        "/api/v1/user/addresses",
        json={
            "type": addr_type,
            "first_name": "Jane",
            "last_name": "Doe",
            "address_line_1": "123 Main St",
            "city": "Springfield",
            "state": "IL",
            "postal_code": "62701",
            "country": "US",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _add_cart_item(
    client: AsyncClient, token: str, product_id: int, quantity: int = 1
) -> dict:
    resp = await client.post(
        "/api/v1/cart/items",
        json={"product_id": product_id, "quantity": quantity},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


_GUEST_ADDR = {
    "first_name": "Guest",
    "last_name": "User",
    "address_line_1": "456 Oak Ave",
    "city": "Chicago",
    "state": "IL",
    "postal_code": "60601",
    "country": "US",
}


# ─── Test: Create order — authenticated ───────────────────────────────────────


async def test_create_order_authenticated_201(order_client):
    admin_token = await _register_admin(order_client, "admin@example.com")
    buyer_token = await _register(order_client, "buyer@example.com", "Buyer")

    cat = await _create_category(order_client, admin_token)
    product = await _create_product(order_client, admin_token, cat["id"])
    addr = await _create_address(order_client, buyer_token)
    await _add_cart_item(order_client, buyer_token, product["id"], 1)

    resp = await order_client.post(
        "/api/v1/orders",
        json={
            "shipping_address_id": addr["id"],
            "payment_method": "paypal",
        },
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert "order" in data
    assert "payment" in data
    assert data["order"]["status"] == "pending_payment"
    assert data["order"]["payment_status"] == "pending"


async def test_create_order_billing_defaults_to_shipping(order_client):
    """When billing_address_id is omitted, billing_address_id should be None in order."""
    admin_token = await _register_admin(order_client, "admin2@example.com")
    buyer_token = await _register(order_client, "buyer2@example.com", "Buyer2")

    cat = await _create_category(order_client, admin_token, slug="watches2")
    product = await _create_product(order_client, admin_token, cat["id"], sku="SKU-002")
    addr = await _create_address(order_client, buyer_token)
    await _add_cart_item(order_client, buyer_token, product["id"])

    resp = await order_client.post(
        "/api/v1/orders",
        json={"shipping_address_id": addr["id"], "payment_method": "paypal"},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()["order"]
    assert data["billing_address_id"] is None


async def test_create_order_with_explicit_billing_address(order_client):
    admin_token = await _register_admin(order_client, "admin3@example.com")
    buyer_token = await _register(order_client, "buyer3@example.com", "Buyer3")

    cat = await _create_category(order_client, admin_token, slug="watches3")
    product = await _create_product(order_client, admin_token, cat["id"], sku="SKU-003")
    shipping_addr = await _create_address(order_client, buyer_token, "shipping")
    billing_addr = await _create_address(order_client, buyer_token, "billing")
    await _add_cart_item(order_client, buyer_token, product["id"])

    resp = await order_client.post(
        "/api/v1/orders",
        json={
            "shipping_address_id": shipping_addr["id"],
            "billing_address_id": billing_addr["id"],
            "payment_method": "paypal",
        },
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()["order"]
    assert data["billing_address_id"] == billing_addr["id"]


async def test_create_order_guest_201(order_client):
    """Guest checkout with email and shipping address object."""
    admin_token = await _register_admin(order_client, "admin4@example.com")

    cat = await _create_category(order_client, admin_token, slug="watches4")
    product = await _create_product(order_client, admin_token, cat["id"], sku="SKU-004")

    # Add item as guest via session
    session_id = "test-session-guest-001"
    resp = await order_client.post(
        "/api/v1/cart/items",
        json={"product_id": product["id"], "quantity": 1},
        headers={"X-Session-ID": session_id},
    )
    assert resp.status_code == 201, resp.text

    resp = await order_client.post(
        "/api/v1/orders",
        json={
            "guest_email": "guest@example.com",
            "shipping_address": _GUEST_ADDR,
            "payment_method": "paypal",
        },
        headers={"X-Session-ID": session_id},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()["order"]
    assert data["guest_email"] == "guest@example.com"
    assert data["user_id"] is None


async def test_create_order_guest_with_billing_address(order_client):
    admin_token = await _register_admin(order_client, "admin5@example.com")

    cat = await _create_category(order_client, admin_token, slug="watches5")
    product = await _create_product(order_client, admin_token, cat["id"], sku="SKU-005")

    session_id = "test-session-guest-002"
    await order_client.post(
        "/api/v1/cart/items",
        json={"product_id": product["id"], "quantity": 1},
        headers={"X-Session-ID": session_id},
    )

    billing_addr = {**_GUEST_ADDR, "first_name": "Bill", "last_name": "Smith"}
    resp = await order_client.post(
        "/api/v1/orders",
        json={
            "guest_email": "guest2@example.com",
            "shipping_address": _GUEST_ADDR,
            "billing_address": billing_addr,
            "payment_method": "paypal",
        },
        headers={"X-Session-ID": session_id},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()["order"]
    assert data["billing_address_id"] is not None


async def test_create_order_decrements_stock(order_client):
    admin_token = await _register_admin(order_client, "admin6@example.com")
    buyer_token = await _register(order_client, "buyer6@example.com", "Buyer6")

    cat = await _create_category(order_client, admin_token, slug="watches6")
    product = await _create_product(
        order_client, admin_token, cat["id"], stock=5, sku="SKU-006"
    )
    addr = await _create_address(order_client, buyer_token)
    await _add_cart_item(order_client, buyer_token, product["id"], 3)

    resp = await order_client.post(
        "/api/v1/orders",
        json={"shipping_address_id": addr["id"], "payment_method": "paypal"},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert resp.status_code == 201, resp.text

    # Check product stock was decremented
    product_resp = await order_client.get(f"/api/v1/products/{product['slug']}")
    assert product_resp.status_code == 200
    assert product_resp.json()["stock_quantity"] == 2


async def test_create_order_items_match_cart(order_client):
    admin_token = await _register_admin(order_client, "admin7@example.com")
    buyer_token = await _register(order_client, "buyer7@example.com", "Buyer7")

    cat = await _create_category(order_client, admin_token, slug="watches7")
    product = await _create_product(
        order_client, admin_token, cat["id"], name="Gold Watch", sku="SKU-007"
    )
    addr = await _create_address(order_client, buyer_token)
    await _add_cart_item(order_client, buyer_token, product["id"], 2)

    resp = await order_client.post(
        "/api/v1/orders",
        json={"shipping_address_id": addr["id"], "payment_method": "paypal"},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert resp.status_code == 201, resp.text
    items = resp.json()["order"]["items"]
    assert len(items) == 1
    assert items[0]["quantity"] == 2
    assert items[0]["product_name"] == "Gold Watch"


async def test_create_order_total_includes_shipping(order_client):
    admin_token = await _register_admin(order_client, "admin8@example.com")
    buyer_token = await _register(order_client, "buyer8@example.com", "Buyer8")

    cat = await _create_category(order_client, admin_token, slug="watches8")
    product = await _create_product(
        order_client, admin_token, cat["id"], price=50.00, sku="SKU-008"
    )
    addr = await _create_address(order_client, buyer_token)
    await _add_cart_item(order_client, buyer_token, product["id"], 2)

    resp = await order_client.post(
        "/api/v1/orders",
        json={"shipping_address_id": addr["id"], "payment_method": "paypal"},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert resp.status_code == 201, resp.text
    order = resp.json()["order"]
    subtotal = float(order["subtotal_amount"])
    shipping = float(order["shipping_cost"])
    total = float(order["total_amount"])
    assert subtotal == pytest.approx(100.0)
    assert shipping == pytest.approx(10.0)
    assert total == pytest.approx(110.0)


# ─── Test: Create order error cases ───────────────────────────────────────────


async def test_create_order_422_empty_cart(order_client):
    token = await _register(order_client, "buyer9@example.com")
    addr = await _create_address(order_client, token)

    resp = await order_client.post(
        "/api/v1/orders",
        json={"shipping_address_id": addr["id"], "payment_method": "paypal"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422
    assert "empty" in resp.json()["detail"].lower()


async def test_create_order_422_no_cart(order_client):
    token = await _register(order_client, "buyer10@example.com")
    addr = await _create_address(order_client, token)

    resp = await order_client.post(
        "/api/v1/orders",
        json={"shipping_address_id": addr["id"], "payment_method": "paypal"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


async def test_create_order_422_insufficient_stock(order_client):
    admin_token = await _register_admin(order_client, "admin11@example.com")
    token2 = await _register(order_client, "buyer11@example.com", "Buyer11")

    cat = await _create_category(order_client, admin_token, slug="watches11")
    product = await _create_product(
        order_client, admin_token, cat["id"], stock=1, sku="SKU-011"
    )
    addr = await _create_address(order_client, token2)

    # Add 1 item (valid), but then reduce stock externally...
    # Instead: add more than stock allows via cart directly (cart allows it if stock was higher)
    # Simpler: add 1 to cart, make stock 0 via another engine, then order
    await _add_cart_item(order_client, token2, product["id"], 1)

    # Drain stock by placing a concurrent order (use raw SQL)
    engine = create_async_engine(settings.database_url, echo=False)
    async with engine.begin() as conn:
        await conn.execute(
            text("UPDATE products SET stock_quantity=0 WHERE id=:id"),
            {"id": product["id"]},
        )
    await engine.dispose()

    resp = await order_client.post(
        "/api/v1/orders",
        json={"shipping_address_id": addr["id"], "payment_method": "paypal"},
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert resp.status_code == 422
    assert "stock" in resp.json()["detail"].lower()


async def test_create_order_422_invalid_payment_method(order_client):
    admin_token = await _register_admin(order_client, "admin12@example.com")
    buyer_token = await _register(order_client, "buyer12@example.com", "Buyer12")

    cat = await _create_category(order_client, admin_token, slug="watches12")
    product = await _create_product(order_client, admin_token, cat["id"], sku="SKU-012")
    addr = await _create_address(order_client, buyer_token)
    await _add_cart_item(order_client, buyer_token, product["id"])

    resp = await order_client.post(
        "/api/v1/orders",
        json={"shipping_address_id": addr["id"], "payment_method": "stripe"},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert resp.status_code == 422
    assert "paypal" in resp.json()["detail"].lower()


async def test_create_order_422_guest_email_missing(order_client):
    admin_token = await _register_admin(order_client, "admin13@example.com")

    cat = await _create_category(order_client, admin_token, slug="watches13")
    product = await _create_product(order_client, admin_token, cat["id"], sku="SKU-013")

    session_id = "test-session-guest-013"
    await order_client.post(
        "/api/v1/cart/items",
        json={"product_id": product["id"], "quantity": 1},
        headers={"X-Session-ID": session_id},
    )

    resp = await order_client.post(
        "/api/v1/orders",
        json={
            "shipping_address": _GUEST_ADDR,
            "payment_method": "paypal",
            # No guest_email
        },
        headers={"X-Session-ID": session_id},
    )
    assert resp.status_code == 422
    assert "email" in resp.json()["detail"].lower()


async def test_create_order_404_address_not_found(order_client):
    admin_token = await _register_admin(order_client, "admin14@example.com")
    buyer_token = await _register(order_client, "buyer14@example.com", "Buyer14")

    cat = await _create_category(order_client, admin_token, slug="watches14")
    product = await _create_product(order_client, admin_token, cat["id"], sku="SKU-014")
    await _add_cart_item(order_client, buyer_token, product["id"])

    resp = await order_client.post(
        "/api/v1/orders",
        json={"shipping_address_id": 999999, "payment_method": "paypal"},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert resp.status_code == 404


async def test_create_order_404_address_wrong_user(order_client):
    admin_token = await _register_admin(order_client, "admin15@example.com")
    buyer_token = await _register(order_client, "buyer15@example.com", "Buyer15")
    buyer_token3 = await _register(order_client, "buyer15b@example.com", "Buyer15B")

    cat = await _create_category(order_client, admin_token, slug="watches15")
    product = await _create_product(order_client, admin_token, cat["id"], sku="SKU-015")
    # Create address for buyer_token3 (wrong user)
    other_addr = await _create_address(order_client, buyer_token3)
    await _add_cart_item(order_client, buyer_token, product["id"])

    resp = await order_client.post(
        "/api/v1/orders",
        json={"shipping_address_id": other_addr["id"], "payment_method": "paypal"},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert resp.status_code == 404


async def test_create_order_order_number_format(order_client):
    admin_token = await _register_admin(order_client, "admin16@example.com")
    buyer_token = await _register(order_client, "buyer16@example.com", "Buyer16")

    cat = await _create_category(order_client, admin_token, slug="watches16")
    product = await _create_product(order_client, admin_token, cat["id"], sku="SKU-016")
    addr = await _create_address(order_client, buyer_token)
    await _add_cart_item(order_client, buyer_token, product["id"])

    resp = await order_client.post(
        "/api/v1/orders",
        json={"shipping_address_id": addr["id"], "payment_method": "paypal"},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert resp.status_code == 201, resp.text
    order_number = resp.json()["order"]["order_number"]
    assert re.match(r"^CM-\d{4}-[0-9A-F]{8}$", order_number), (
        f"Invalid format: {order_number}"
    )


# ─── Test: No auth → 401 for order creation ──────────────────────────────────


async def test_create_order_401_no_auth(order_client):
    resp = await order_client.post(
        "/api/v1/orders",
        json={"payment_method": "paypal"},
    )
    assert resp.status_code == 401


# ─── Test: List orders ────────────────────────────────────────────────────────


async def test_list_orders_200(order_client):
    admin_token = await _register_admin(order_client, "admin17@example.com")
    buyer_token = await _register(order_client, "buyer17@example.com", "Buyer17")

    cat = await _create_category(order_client, admin_token, slug="watches17")
    product = await _create_product(order_client, admin_token, cat["id"], sku="SKU-017")
    addr = await _create_address(order_client, buyer_token)
    await _add_cart_item(order_client, buyer_token, product["id"])
    await order_client.post(
        "/api/v1/orders",
        json={"shipping_address_id": addr["id"], "payment_method": "paypal"},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )

    resp = await order_client.get(
        "/api/v1/user/orders",
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["page"] == 1
    assert data["size"] == 10


async def test_list_orders_empty(order_client):
    token = await _register(order_client, "buyer18@example.com")
    resp = await order_client.get(
        "/api/v1/user/orders",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []


async def test_list_orders_401(order_client):
    resp = await order_client.get("/api/v1/user/orders")
    assert resp.status_code == 401


async def test_list_orders_pagination(order_client):
    admin_token = await _register_admin(order_client, "admin19@example.com")
    buyer_token = await _register(order_client, "buyer19@example.com", "Buyer19")

    cat = await _create_category(order_client, admin_token, slug="watches19")
    addr = await _create_address(order_client, buyer_token)

    # Create 3 orders (3 separate products to avoid stock issues)
    for i in range(3):
        product = await _create_product(
            order_client,
            admin_token,
            cat["id"],
            name=f"Watch {i}",
            sku=f"SKU-019-{i}",
            stock=5,
        )
        await _add_cart_item(order_client, buyer_token, product["id"])
        resp = await order_client.post(
            "/api/v1/orders",
            json={"shipping_address_id": addr["id"], "payment_method": "paypal"},
            headers={"Authorization": f"Bearer {buyer_token}"},
        )
        assert resp.status_code == 201, resp.text

    # Page 1, size 2
    resp = await order_client.get(
        "/api/v1/user/orders?page=1&size=2",
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert len(data["items"]) == 2
    assert data["pages"] == 2

    # Page 2, size 2
    resp = await order_client.get(
        "/api/v1/user/orders?page=2&size=2",
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 1


# ─── Test: Get single order ───────────────────────────────────────────────────


async def test_get_order_200(order_client):
    admin_token = await _register_admin(order_client, "admin20@example.com")
    buyer_token = await _register(order_client, "buyer20@example.com", "Buyer20")

    cat = await _create_category(order_client, admin_token, slug="watches20")
    product = await _create_product(order_client, admin_token, cat["id"], sku="SKU-020")
    addr = await _create_address(order_client, buyer_token)
    await _add_cart_item(order_client, buyer_token, product["id"])

    create_resp = await order_client.post(
        "/api/v1/orders",
        json={"shipping_address_id": addr["id"], "payment_method": "paypal"},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert create_resp.status_code == 201
    order_number = create_resp.json()["order"]["order_number"]

    resp = await order_client.get(
        f"/api/v1/user/orders/{order_number}",
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["order_number"] == order_number
    assert "items" in data
    assert "status_label" in data
    assert "payment_status_label" in data


async def test_get_order_404_wrong_user(order_client):
    admin_token = await _register_admin(order_client, "admin21@example.com")
    buyer_token = await _register(order_client, "buyer21@example.com", "Buyer21")
    buyer_token3 = await _register(order_client, "buyer21b@example.com", "Buyer21B")

    cat = await _create_category(order_client, admin_token, slug="watches21")
    product = await _create_product(order_client, admin_token, cat["id"], sku="SKU-021")
    addr = await _create_address(order_client, buyer_token)
    await _add_cart_item(order_client, buyer_token, product["id"])

    create_resp = await order_client.post(
        "/api/v1/orders",
        json={"shipping_address_id": addr["id"], "payment_method": "paypal"},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    order_number = create_resp.json()["order"]["order_number"]

    resp = await order_client.get(
        f"/api/v1/user/orders/{order_number}",
        headers={"Authorization": f"Bearer {buyer_token3}"},
    )
    assert resp.status_code == 404


async def test_get_order_404_nonexistent(order_client):
    token = await _register(order_client, "buyer22@example.com")
    resp = await order_client.get(
        "/api/v1/user/orders/CM-9999-DEADBEEF",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


async def test_get_order_401(order_client):
    resp = await order_client.get("/api/v1/user/orders/CM-2024-DEADBEEF")
    assert resp.status_code == 401


# ─── Test: Partial stock rollback ─────────────────────────────────────────────


async def test_create_order_422_partial_stock_rollback(order_client):
    """Two products in cart; second has insufficient stock → first NOT decremented."""
    admin_token = await _register_admin(order_client, "admin23@example.com")
    buyer_token = await _register(order_client, "buyer23@example.com", "Buyer23")

    cat = await _create_category(order_client, admin_token, slug="watches23")
    product1 = await _create_product(
        order_client, admin_token, cat["id"], stock=5, sku="SKU-023-A", name="Watch A"
    )
    product2 = await _create_product(
        order_client, admin_token, cat["id"], stock=1, sku="SKU-023-B", name="Watch B"
    )
    addr = await _create_address(order_client, buyer_token)

    await _add_cart_item(order_client, buyer_token, product1["id"], 2)
    await _add_cart_item(order_client, buyer_token, product2["id"], 1)

    # Drain product2 stock so order fails on it
    engine = create_async_engine(settings.database_url, echo=False)
    async with engine.begin() as conn:
        await conn.execute(
            text("UPDATE products SET stock_quantity=0 WHERE id=:id"),
            {"id": product2["id"]},
        )
    await engine.dispose()

    resp = await order_client.post(
        "/api/v1/orders",
        json={"shipping_address_id": addr["id"], "payment_method": "paypal"},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert resp.status_code == 422

    # Product1 stock must NOT have been decremented (transaction rolled back)
    product1_resp = await order_client.get(f"/api/v1/products/{product1['slug']}")
    assert product1_resp.json()["stock_quantity"] == 5
