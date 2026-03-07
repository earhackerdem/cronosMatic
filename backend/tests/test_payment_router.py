"""API integration tests for PayPal payment endpoints."""

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
async def payment_client():
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
                "TRUNCATE TABLE order_items, orders, addresses, cart_items, carts, "
                "products, categories, refresh_tokens, users RESTART IDENTITY CASCADE"
            )
        )

    await engine.dispose()


# ─── Helper functions ─────────────────────────────────────────────────────────


async def _register(client: AsyncClient, email: str, name: str = "Test User") -> str:
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
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "password123"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


async def _make_admin(client: AsyncClient, email: str) -> None:
    engine = create_async_engine(settings.database_url, echo=False)
    async with engine.begin() as conn:
        await conn.execute(
            text("UPDATE users SET is_admin=true WHERE email=:email"),
            {"email": email},
        )
    await engine.dispose()


async def _register_admin(client: AsyncClient, email: str, name: str = "Admin") -> str:
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


async def _add_guest_cart_item(
    client: AsyncClient, session_id: str, product_id: int, quantity: int = 1
) -> dict:
    resp = await client.post(
        "/api/v1/cart/items",
        json={"product_id": product_id, "quantity": quantity},
        headers={"X-Session-ID": session_id},
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


async def _create_order(
    client: AsyncClient,
    token: str,
    shipping_address_id: int,
) -> dict:
    """Create an order for an authenticated user and return the order dict."""
    resp = await client.post(
        "/api/v1/orders",
        json={"shipping_address_id": shipping_address_id, "payment_method": "paypal"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["order"]


async def _create_guest_order(
    client: AsyncClient,
    session_id: str,
) -> dict:
    """Create an order for a guest user and return the order dict."""
    resp = await client.post(
        "/api/v1/orders",
        json={
            "guest_email": "guest@example.com",
            "shipping_address": _GUEST_ADDR,
            "payment_method": "paypal",
        },
        headers={"X-Session-ID": session_id},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["order"]


# ─── Test: simulate-success ───────────────────────────────────────────────────


async def test_simulate_success_200_authenticated(payment_client):
    admin_token = await _register_admin(payment_client, "admin01@example.com")
    buyer_token = await _register(payment_client, "buyer01@example.com", "Buyer01")

    cat = await _create_category(payment_client, admin_token, slug="p01")
    product = await _create_product(payment_client, admin_token, cat["id"], sku="P-01")
    addr = await _create_address(payment_client, buyer_token)
    await _add_cart_item(payment_client, buyer_token, product["id"])
    order = await _create_order(payment_client, buyer_token, addr["id"])

    resp = await payment_client.post(
        "/api/v1/payments/paypal/simulate-success",
        json={"order_id": order["id"]},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["order_number"] == order["order_number"]
    assert data["payment_status"] == "paid"
    assert data["simulated"] is True
    assert data["paypal_order_id"].startswith("SIMULATED_")
    assert data["capture_id"].startswith("CAPTURE_")


async def test_simulate_success_200_guest(payment_client):
    admin_token = await _register_admin(payment_client, "admin02@example.com")

    cat = await _create_category(payment_client, admin_token, slug="p02")
    product = await _create_product(payment_client, admin_token, cat["id"], sku="P-02")

    session_id = "test-pay-guest-001"
    await _add_guest_cart_item(payment_client, session_id, product["id"])
    order = await _create_guest_order(payment_client, session_id)

    resp = await payment_client.post(
        "/api/v1/payments/paypal/simulate-success",
        json={"order_id": order["id"]},
        headers={"X-Session-ID": session_id},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["payment_status"] == "paid"
    assert data["simulated"] is True


async def test_simulate_success_clears_cart(payment_client):
    admin_token = await _register_admin(payment_client, "admin03@example.com")
    buyer_token = await _register(payment_client, "buyer03@example.com", "Buyer03")

    cat = await _create_category(payment_client, admin_token, slug="p03")
    product = await _create_product(payment_client, admin_token, cat["id"], sku="P-03")
    addr = await _create_address(payment_client, buyer_token)
    await _add_cart_item(payment_client, buyer_token, product["id"])
    order = await _create_order(payment_client, buyer_token, addr["id"])

    # The order service does not clear the cart; simulate-success does.
    # Add another item so the cart is non-empty going into the payment call.
    await _add_cart_item(payment_client, buyer_token, product["id"])

    resp = await payment_client.post(
        "/api/v1/payments/paypal/simulate-success",
        json={"order_id": order["id"]},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert resp.status_code == 200, resp.text

    # Cart should be cleared
    cart_resp = await payment_client.get(
        "/api/v1/cart",
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert cart_resp.status_code == 200
    assert cart_resp.json()["total_items"] == 0


async def test_simulate_success_transitions_order_to_processing(payment_client):
    admin_token = await _register_admin(payment_client, "admin04@example.com")
    buyer_token = await _register(payment_client, "buyer04@example.com", "Buyer04")

    cat = await _create_category(payment_client, admin_token, slug="p04")
    product = await _create_product(payment_client, admin_token, cat["id"], sku="P-04")
    addr = await _create_address(payment_client, buyer_token)
    await _add_cart_item(payment_client, buyer_token, product["id"])
    order = await _create_order(payment_client, buyer_token, addr["id"])

    assert order["status"] == "pending_payment"

    resp = await payment_client.post(
        "/api/v1/payments/paypal/simulate-success",
        json={"order_id": order["id"]},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert resp.status_code == 200, resp.text

    # Fetch the order to verify status change
    order_resp = await payment_client.get(
        f"/api/v1/user/orders/{order['order_number']}",
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert order_resp.status_code == 200
    updated = order_resp.json()
    assert updated["status"] == "processing"
    assert updated["payment_status"] == "paid"


async def test_simulate_success_updates_payment_fields(payment_client):
    admin_token = await _register_admin(payment_client, "admin05@example.com")
    buyer_token = await _register(payment_client, "buyer05@example.com", "Buyer05")

    cat = await _create_category(payment_client, admin_token, slug="p05")
    product = await _create_product(payment_client, admin_token, cat["id"], sku="P-05")
    addr = await _create_address(payment_client, buyer_token)
    await _add_cart_item(payment_client, buyer_token, product["id"])
    order = await _create_order(payment_client, buyer_token, addr["id"])

    resp = await payment_client.post(
        "/api/v1/payments/paypal/simulate-success",
        json={"order_id": order["id"]},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()

    # Verify payment_gateway and payment_id were set on the order
    order_resp = await payment_client.get(
        f"/api/v1/user/orders/{order['order_number']}",
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    updated = order_resp.json()
    assert updated["payment_gateway"] == "paypal"
    assert updated["payment_id"] == data["capture_id"]


# ─── Test: simulate-failure ───────────────────────────────────────────────────


async def test_simulate_failure_200(payment_client):
    admin_token = await _register_admin(payment_client, "admin06@example.com")
    buyer_token = await _register(payment_client, "buyer06@example.com", "Buyer06")

    cat = await _create_category(payment_client, admin_token, slug="p06")
    product = await _create_product(payment_client, admin_token, cat["id"], sku="P-06")
    addr = await _create_address(payment_client, buyer_token)
    await _add_cart_item(payment_client, buyer_token, product["id"])
    order = await _create_order(payment_client, buyer_token, addr["id"])

    resp = await payment_client.post(
        "/api/v1/payments/paypal/simulate-failure",
        json={"order_id": order["id"]},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["order_number"] == order["order_number"]
    assert data["payment_status"] == "failed"
    assert data["simulated"] is True
    assert data["paypal_order_id"].startswith("FAILED_")
    assert "declined" in data["error"].lower()


async def test_simulate_failure_does_not_clear_cart(payment_client):
    admin_token = await _register_admin(payment_client, "admin07@example.com")
    buyer_token = await _register(payment_client, "buyer07@example.com", "Buyer07")

    cat = await _create_category(payment_client, admin_token, slug="p07")
    product = await _create_product(payment_client, admin_token, cat["id"], sku="P-07")
    addr = await _create_address(payment_client, buyer_token)
    await _add_cart_item(payment_client, buyer_token, product["id"])
    order = await _create_order(payment_client, buyer_token, addr["id"])

    # Add an item to the cart after order creation to verify cart is NOT cleared
    await _add_cart_item(payment_client, buyer_token, product["id"])

    resp = await payment_client.post(
        "/api/v1/payments/paypal/simulate-failure",
        json={"order_id": order["id"]},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert resp.status_code == 200, resp.text

    # Cart should NOT be cleared on failure
    cart_resp = await payment_client.get(
        "/api/v1/cart",
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert cart_resp.status_code == 200
    assert cart_resp.json()["total_items"] > 0


async def test_simulate_failure_does_not_cancel_order(payment_client):
    admin_token = await _register_admin(payment_client, "admin08@example.com")
    buyer_token = await _register(payment_client, "buyer08@example.com", "Buyer08")

    cat = await _create_category(payment_client, admin_token, slug="p08")
    product = await _create_product(payment_client, admin_token, cat["id"], sku="P-08")
    addr = await _create_address(payment_client, buyer_token)
    await _add_cart_item(payment_client, buyer_token, product["id"])
    order = await _create_order(payment_client, buyer_token, addr["id"])

    resp = await payment_client.post(
        "/api/v1/payments/paypal/simulate-failure",
        json={"order_id": order["id"]},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert resp.status_code == 200, resp.text

    # Order status should remain pending_payment (not cancelled)
    order_resp = await payment_client.get(
        f"/api/v1/user/orders/{order['order_number']}",
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert order_resp.status_code == 200
    updated = order_resp.json()
    assert updated["status"] == "pending_payment"
    assert updated["payment_status"] == "failed"


# ─── Test: simulate disabled ──────────────────────────────────────────────────


async def test_simulate_endpoints_403_when_disabled(payment_client, monkeypatch):
    monkeypatch.setattr(settings, "paypal_simulate_payments", False)

    admin_token = await _register_admin(payment_client, "admin09@example.com")
    buyer_token = await _register(payment_client, "buyer09@example.com", "Buyer09")

    cat = await _create_category(payment_client, admin_token, slug="p09")
    product = await _create_product(payment_client, admin_token, cat["id"], sku="P-09")
    addr = await _create_address(payment_client, buyer_token)
    await _add_cart_item(payment_client, buyer_token, product["id"])
    order = await _create_order(payment_client, buyer_token, addr["id"])

    resp = await payment_client.post(
        "/api/v1/payments/paypal/simulate-success",
        json={"order_id": order["id"]},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert resp.status_code == 403
    assert "disabled" in resp.json()["detail"].lower()


async def test_simulate_failure_403_when_disabled(payment_client, monkeypatch):
    monkeypatch.setattr(settings, "paypal_simulate_payments", False)

    admin_token = await _register_admin(payment_client, "admin10@example.com")
    buyer_token = await _register(payment_client, "buyer10@example.com", "Buyer10")

    cat = await _create_category(payment_client, admin_token, slug="p10")
    product = await _create_product(payment_client, admin_token, cat["id"], sku="P-10")
    addr = await _create_address(payment_client, buyer_token)
    await _add_cart_item(payment_client, buyer_token, product["id"])
    order = await _create_order(payment_client, buyer_token, addr["id"])

    resp = await payment_client.post(
        "/api/v1/payments/paypal/simulate-failure",
        json={"order_id": order["id"]},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert resp.status_code == 403
    assert "disabled" in resp.json()["detail"].lower()


# ─── Test: create-order ───────────────────────────────────────────────────────


async def test_create_paypal_order_200_simulated(payment_client):
    admin_token = await _register_admin(payment_client, "admin11@example.com")
    buyer_token = await _register(payment_client, "buyer11@example.com", "Buyer11")

    cat = await _create_category(payment_client, admin_token, slug="p11")
    product = await _create_product(payment_client, admin_token, cat["id"], sku="P-11")
    addr = await _create_address(payment_client, buyer_token)
    await _add_cart_item(payment_client, buyer_token, product["id"])
    order = await _create_order(payment_client, buyer_token, addr["id"])

    resp = await payment_client.post(
        "/api/v1/payments/paypal/create-order",
        json={"order_id": order["id"]},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["order_number"] == order["order_number"]
    assert data["paypal_order_id"].startswith("SIMULATED_")
    assert "sandbox.paypal.com" in data["approval_url"]


async def test_create_paypal_order_404_not_found(payment_client):
    buyer_token = await _register(payment_client, "buyer12@example.com", "Buyer12")

    resp = await payment_client.post(
        "/api/v1/payments/paypal/create-order",
        json={"order_id": 999999},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert resp.status_code == 404


async def test_create_paypal_order_404_wrong_owner(payment_client):
    admin_token = await _register_admin(payment_client, "admin13@example.com")
    buyer_token = await _register(payment_client, "buyer13@example.com", "Buyer13")
    other_token = await _register(payment_client, "other13@example.com", "Other13")

    cat = await _create_category(payment_client, admin_token, slug="p13")
    product = await _create_product(payment_client, admin_token, cat["id"], sku="P-13")
    addr = await _create_address(payment_client, buyer_token)
    await _add_cart_item(payment_client, buyer_token, product["id"])
    order = await _create_order(payment_client, buyer_token, addr["id"])

    resp = await payment_client.post(
        "/api/v1/payments/paypal/create-order",
        json={"order_id": order["id"]},
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert resp.status_code == 404


async def test_create_paypal_order_422_already_paid(payment_client):
    admin_token = await _register_admin(payment_client, "admin14@example.com")
    buyer_token = await _register(payment_client, "buyer14@example.com", "Buyer14")

    cat = await _create_category(payment_client, admin_token, slug="p14")
    product = await _create_product(payment_client, admin_token, cat["id"], sku="P-14")
    addr = await _create_address(payment_client, buyer_token)
    await _add_cart_item(payment_client, buyer_token, product["id"])
    order = await _create_order(payment_client, buyer_token, addr["id"])

    # Mark as paid via simulate-success
    resp = await payment_client.post(
        "/api/v1/payments/paypal/simulate-success",
        json={"order_id": order["id"]},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert resp.status_code == 200

    # Now try to create-order again — should fail with 422
    resp2 = await payment_client.post(
        "/api/v1/payments/paypal/create-order",
        json={"order_id": order["id"]},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert resp2.status_code == 422
    assert "pending" in resp2.json()["detail"].lower()


async def test_create_paypal_order_401_no_auth(payment_client):
    resp = await payment_client.post(
        "/api/v1/payments/paypal/create-order",
        json={"order_id": 1},
    )
    assert resp.status_code == 401


# ─── Test: capture-order ──────────────────────────────────────────────────────


async def test_capture_paypal_order_200(payment_client):
    admin_token = await _register_admin(payment_client, "admin15@example.com")
    buyer_token = await _register(payment_client, "buyer15@example.com", "Buyer15")

    cat = await _create_category(payment_client, admin_token, slug="p15")
    product = await _create_product(payment_client, admin_token, cat["id"], sku="P-15")
    addr = await _create_address(payment_client, buyer_token)
    await _add_cart_item(payment_client, buyer_token, product["id"])
    order = await _create_order(payment_client, buyer_token, addr["id"])

    # First create a paypal order to get a paypal_order_id
    create_resp = await payment_client.post(
        "/api/v1/payments/paypal/create-order",
        json={"order_id": order["id"]},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert create_resp.status_code == 200
    paypal_order_id = create_resp.json()["paypal_order_id"]

    # Now capture it
    resp = await payment_client.post(
        "/api/v1/payments/paypal/capture-order",
        json={"order_id": order["id"], "paypal_order_id": paypal_order_id},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["order_number"] == order["order_number"]
    assert data["payment_status"] == "paid"
    assert data["capture_id"].startswith("CAPTURE_")


async def test_capture_paypal_order_422_already_paid(payment_client):
    admin_token = await _register_admin(payment_client, "admin16@example.com")
    buyer_token = await _register(payment_client, "buyer16@example.com", "Buyer16")

    cat = await _create_category(payment_client, admin_token, slug="p16")
    product = await _create_product(payment_client, admin_token, cat["id"], sku="P-16")
    addr = await _create_address(payment_client, buyer_token)
    await _add_cart_item(payment_client, buyer_token, product["id"])
    order = await _create_order(payment_client, buyer_token, addr["id"])

    # Simulate success first
    await payment_client.post(
        "/api/v1/payments/paypal/simulate-success",
        json={"order_id": order["id"]},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )

    # Attempt capture again — should fail with 422
    resp = await payment_client.post(
        "/api/v1/payments/paypal/capture-order",
        json={"order_id": order["id"], "paypal_order_id": "SOME_PAYPAL_ID"},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert resp.status_code == 422
    assert "pending" in resp.json()["detail"].lower()


async def test_capture_paypal_order_clears_cart(payment_client):
    admin_token = await _register_admin(payment_client, "admin17@example.com")
    buyer_token = await _register(payment_client, "buyer17@example.com", "Buyer17")

    cat = await _create_category(payment_client, admin_token, slug="p17")
    product = await _create_product(payment_client, admin_token, cat["id"], sku="P-17")
    addr = await _create_address(payment_client, buyer_token)
    await _add_cart_item(payment_client, buyer_token, product["id"])
    order = await _create_order(payment_client, buyer_token, addr["id"])

    # Add an item to the cart after order creation
    await _add_cart_item(payment_client, buyer_token, product["id"])

    create_resp = await payment_client.post(
        "/api/v1/payments/paypal/create-order",
        json={"order_id": order["id"]},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    paypal_order_id = create_resp.json()["paypal_order_id"]

    resp = await payment_client.post(
        "/api/v1/payments/paypal/capture-order",
        json={"order_id": order["id"], "paypal_order_id": paypal_order_id},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert resp.status_code == 200, resp.text

    # Cart should be cleared
    cart_resp = await payment_client.get(
        "/api/v1/cart",
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert cart_resp.status_code == 200
    assert cart_resp.json()["total_items"] == 0


# ─── Test: verify-config ──────────────────────────────────────────────────────


async def test_verify_config_200_admin(payment_client):
    admin_token = await _register_admin(payment_client, "admin18@example.com")

    resp = await payment_client.get(
        "/api/v1/payments/paypal/verify-config",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "mode" in data
    assert "simulate_payments" in data
    assert "client_id_configured" in data
    assert "client_secret_configured" in data
    assert "base_url" in data
    assert "auth_test" in data
    assert data["simulate_payments"] is True


async def test_verify_config_403_non_admin(payment_client):
    token = await _register(payment_client, "buyer19@example.com", "Buyer19")

    resp = await payment_client.get(
        "/api/v1/payments/paypal/verify-config",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


async def test_verify_config_401_unauthenticated(payment_client):
    resp = await payment_client.get("/api/v1/payments/paypal/verify-config")
    assert resp.status_code == 401


# ─── Test: double simulate → 422 ─────────────────────────────────────────────


async def test_simulate_success_422_already_processed(payment_client):
    """Calling simulate-success twice on the same order should return 422 on the second call."""
    admin_token = await _register_admin(payment_client, "admin20@example.com")
    buyer_token = await _register(payment_client, "buyer20@example.com", "Buyer20")

    cat = await _create_category(payment_client, admin_token, slug="p20")
    product = await _create_product(payment_client, admin_token, cat["id"], sku="P-20")
    addr = await _create_address(payment_client, buyer_token)
    await _add_cart_item(payment_client, buyer_token, product["id"])
    order = await _create_order(payment_client, buyer_token, addr["id"])

    # First simulate-success — should succeed
    resp1 = await payment_client.post(
        "/api/v1/payments/paypal/simulate-success",
        json={"order_id": order["id"]},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert resp1.status_code == 200

    # Second simulate-success — should fail with 422 (payment_status is no longer pending)
    resp2 = await payment_client.post(
        "/api/v1/payments/paypal/simulate-success",
        json={"order_id": order["id"]},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert resp2.status_code == 422
    assert "pending" in resp2.json()["detail"].lower()
