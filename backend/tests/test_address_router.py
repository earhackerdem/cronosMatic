"""API integration tests for user address endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.db.base import Base
from app.db.engine import get_db_session
from app.main import app
from app.models.address import AddressModel  # noqa: F401
from app.models.user import UserModel  # noqa: F401


# ─── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
async def addr_client():
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
                "TRUNCATE TABLE addresses, cart_items, carts, products, categories, refresh_tokens, users RESTART IDENTITY CASCADE"
            )
        )

    await engine.dispose()


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


@pytest.fixture
async def token(addr_client):
    return await _register(addr_client, "user@example.com", "User One")


@pytest.fixture
async def token_b(addr_client):
    return await _register(addr_client, "userb@example.com", "User Two")


_BASE = "/api/v1/user/addresses"

_SHIPPING_PAYLOAD = {
    "type": "shipping",
    "first_name": "Jane",
    "last_name": "Doe",
    "address_line_1": "123 Main St",
    "city": "Springfield",
    "state": "IL",
    "postal_code": "62701",
    "country": "US",
}

_BILLING_PAYLOAD = {
    "type": "billing",
    "first_name": "John",
    "last_name": "Smith",
    "address_line_1": "456 Oak Ave",
    "city": "Chicago",
    "state": "IL",
    "postal_code": "60601",
    "country": "US",
}


async def _create(client: AsyncClient, token: str, payload: dict) -> dict:
    resp = await client.post(
        _BASE,
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# ─── AC1: Unauthenticated → 401 ──────────────────────────────────────────────


async def test_list_401_without_token(addr_client):
    resp = await addr_client.get(_BASE)
    assert resp.status_code == 401


async def test_create_401_without_token(addr_client):
    resp = await addr_client.post(_BASE, json=_SHIPPING_PAYLOAD)
    assert resp.status_code == 401


async def test_get_401_without_token(addr_client):
    resp = await addr_client.get(f"{_BASE}/1")
    assert resp.status_code == 401


async def test_update_401_without_token(addr_client):
    resp = await addr_client.put(f"{_BASE}/1", json={"city": "Other"})
    assert resp.status_code == 401


async def test_delete_401_without_token(addr_client):
    resp = await addr_client.delete(f"{_BASE}/1")
    assert resp.status_code == 401


async def test_set_default_401_without_token(addr_client):
    resp = await addr_client.patch(f"{_BASE}/1/set-default")
    assert resp.status_code == 401


# ─── AC2: List shows only the authenticated user's addresses ──────────────────


async def test_list_shows_only_own_addresses(addr_client, token, token_b):
    await _create(addr_client, token, _SHIPPING_PAYLOAD)
    await _create(addr_client, token_b, _BILLING_PAYLOAD)

    resp = await addr_client.get(_BASE, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["type"] == "shipping"


# ─── AC3: Filter by ?type= ─────────────────────────────────────────────────────


async def test_list_filter_by_type(addr_client, token):
    await _create(addr_client, token, _SHIPPING_PAYLOAD)
    await _create(addr_client, token, _BILLING_PAYLOAD)

    resp = await addr_client.get(
        f"{_BASE}?type=shipping",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["type"] == "shipping"


async def test_list_filter_by_billing_type(addr_client, token):
    await _create(addr_client, token, _SHIPPING_PAYLOAD)
    await _create(addr_client, token, _BILLING_PAYLOAD)

    resp = await addr_client.get(
        f"{_BASE}?type=billing",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["type"] == "billing"


# ─── AC4: Sorted by default first, then created_at desc ──────────────────────


async def test_list_sorted_default_first(addr_client, token):
    a1 = await _create(addr_client, token, _SHIPPING_PAYLOAD)
    a2 = await _create(
        addr_client,
        token,
        {**_SHIPPING_PAYLOAD, "address_line_1": "999 Second St", "is_default": True},
    )

    resp = await addr_client.get(_BASE, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data[0]["id"] == a2["id"]
    assert data[0]["is_default"] is True
    assert data[1]["id"] == a1["id"]


# ─── AC5: Creating with valid data returns 201 ────────────────────────────────


async def test_create_returns_201(addr_client, token):
    resp = await addr_client.post(
        _BASE,
        json=_SHIPPING_PAYLOAD,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["id"] is not None
    assert data["type"] == "shipping"
    assert data["city"] == "Springfield"


# ─── AC6: Required fields validated (422 if missing) ─────────────────────────


async def test_create_422_missing_required_fields(addr_client, token):
    resp = await addr_client.post(
        _BASE,
        json={"type": "shipping"},  # Missing required fields
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


# ─── AC7: Type must be shipping or billing ────────────────────────────────────


async def test_create_422_invalid_type(addr_client, token):
    resp = await addr_client.post(
        _BASE,
        json={**_SHIPPING_PAYLOAD, "type": "invalid"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


# ─── AC8: full_name and full_address computed correctly ──────────────────────


async def test_response_full_name_computed(addr_client, token):
    data = await _create(addr_client, token, _SHIPPING_PAYLOAD)
    assert data["full_name"] == "Jane Doe"


async def test_response_full_address_computed(addr_client, token):
    data = await _create(addr_client, token, _SHIPPING_PAYLOAD)
    assert "123 Main St" in data["full_address"]
    assert "Springfield" in data["full_address"]
    assert "62701" in data["full_address"]
    assert "US" in data["full_address"]


async def test_response_full_address_with_line2(addr_client, token):
    payload = {**_SHIPPING_PAYLOAD, "address_line_2": "Apt 4B"}
    data = await _create(addr_client, token, payload)
    assert "Apt 4B" in data["full_address"]


# ─── AC9: Cannot view another user's address (404) ───────────────────────────


async def test_get_404_other_users_address(addr_client, token, token_b):
    addr = await _create(addr_client, token, _SHIPPING_PAYLOAD)
    resp = await addr_client.get(
        f"{_BASE}/{addr['id']}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp.status_code == 404


# ─── AC10: Cannot update another user's address (404) ────────────────────────


async def test_update_404_other_users_address(addr_client, token, token_b):
    addr = await _create(addr_client, token, _SHIPPING_PAYLOAD)
    resp = await addr_client.put(
        f"{_BASE}/{addr['id']}",
        json={"city": "Hackerville"},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp.status_code == 404


# ─── AC11: Cannot delete another user's address (404) ────────────────────────


async def test_delete_404_other_users_address(addr_client, token, token_b):
    addr = await _create(addr_client, token, _SHIPPING_PAYLOAD)
    resp = await addr_client.delete(
        f"{_BASE}/{addr['id']}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp.status_code == 404


# ─── AC12: Creating as default deactivates other defaults of same type ────────


async def test_create_default_clears_other_defaults(addr_client, token):
    first = await _create(addr_client, token, {**_SHIPPING_PAYLOAD, "is_default": True})
    assert first["is_default"] is True

    second = await _create(
        addr_client,
        token,
        {**_SHIPPING_PAYLOAD, "address_line_1": "999 New St", "is_default": True},
    )
    assert second["is_default"] is True

    # First should now be non-default
    resp = await addr_client.get(
        f"{_BASE}/{first['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.json()["is_default"] is False


# ─── AC13: Updating to default deactivates other defaults of same type ────────


async def test_update_to_default_clears_other_defaults(addr_client, token):
    first = await _create(addr_client, token, {**_SHIPPING_PAYLOAD, "is_default": True})
    second = await _create(
        addr_client, token, {**_SHIPPING_PAYLOAD, "address_line_1": "999 New St"}
    )
    assert second["is_default"] is False

    # Set second as default via update
    resp = await addr_client.put(
        f"{_BASE}/{second['id']}",
        json={"is_default": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["is_default"] is True

    # First should now be non-default
    resp = await addr_client.get(
        f"{_BASE}/{first['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.json()["is_default"] is False


# ─── AC14: set-default deactivates previous default of same type ──────────────


async def test_set_default_deactivates_previous_default(addr_client, token):
    first = await _create(addr_client, token, {**_SHIPPING_PAYLOAD, "is_default": True})
    second = await _create(
        addr_client, token, {**_SHIPPING_PAYLOAD, "address_line_1": "999 New St"}
    )

    resp = await addr_client.patch(
        f"{_BASE}/{second['id']}/set-default",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["is_default"] is True

    resp = await addr_client.get(
        f"{_BASE}/{first['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.json()["is_default"] is False


# ─── AC15: Defaults of different types coexist ───────────────────────────────


async def test_default_shipping_and_billing_coexist(addr_client, token):
    shipping = await _create(
        addr_client, token, {**_SHIPPING_PAYLOAD, "is_default": True}
    )
    billing = await _create(
        addr_client, token, {**_BILLING_PAYLOAD, "is_default": True}
    )

    resp_s = await addr_client.get(
        f"{_BASE}/{shipping['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    resp_b = await addr_client.get(
        f"{_BASE}/{billing['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp_s.json()["is_default"] is True
    assert resp_b.json()["is_default"] is True


# ─── AC16: Cannot set-default on another user's address (404) ────────────────


async def test_set_default_404_other_users_address(addr_client, token, token_b):
    addr = await _create(addr_client, token, _SHIPPING_PAYLOAD)
    resp = await addr_client.patch(
        f"{_BASE}/{addr['id']}/set-default",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp.status_code == 404


# ─── AC17: DELETE returns 204 ────────────────────────────────────────────────


async def test_delete_returns_204(addr_client, token):
    addr = await _create(addr_client, token, _SHIPPING_PAYLOAD)
    resp = await addr_client.delete(
        f"{_BASE}/{addr['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 204
    assert resp.content == b""


async def test_delete_removes_address(addr_client, token):
    addr = await _create(addr_client, token, _SHIPPING_PAYLOAD)
    await addr_client.delete(
        f"{_BASE}/{addr['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    resp = await addr_client.get(
        f"{_BASE}/{addr['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


# ─── Additional edge cases ────────────────────────────────────────────────────


async def test_get_404_nonexistent_address(addr_client, token):
    resp = await addr_client.get(
        f"{_BASE}/999999",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


async def test_list_empty_when_no_addresses(addr_client, token):
    resp = await addr_client.get(
        _BASE,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json() == []


async def test_update_fields_partially(addr_client, token):
    addr = await _create(addr_client, token, _SHIPPING_PAYLOAD)
    resp = await addr_client.put(
        f"{_BASE}/{addr['id']}",
        json={"city": "New York"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["city"] == "New York"
    assert data["first_name"] == "Jane"  # unchanged


async def test_optional_fields_in_response(addr_client, token):
    payload = {
        **_SHIPPING_PAYLOAD,
        "company": "ACME Corp",
        "address_line_2": "Suite 200",
        "phone": "+1-555-0100",
    }
    data = await _create(addr_client, token, payload)
    assert data["company"] == "ACME Corp"
    assert data["address_line_2"] == "Suite 200"
    assert data["phone"] == "+1-555-0100"


async def test_response_does_not_include_user_id(addr_client, token):
    data = await _create(addr_client, token, _SHIPPING_PAYLOAD)
    assert "user_id" not in data
