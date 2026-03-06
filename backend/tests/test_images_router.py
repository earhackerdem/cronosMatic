"""API integration tests for admin image upload endpoint."""

from unittest.mock import MagicMock, patch

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
async def img_client():
    """HTTP client with per-test DB session."""
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
async def admin_token(img_client):
    """Register an admin user and return a bearer token."""
    resp = await img_client.post(
        "/api/v1/auth/register",
        json={
            "name": "Admin User",
            "email": "admin@images.example.com",
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
            .where(UserModel.email == "admin@images.example.com")
            .values(is_admin=True)
        )
        await session.commit()
    await engine.dispose()

    return token


@pytest.fixture
async def user_token(img_client):
    """Register a non-admin user and return a bearer token."""
    resp = await img_client.post(
        "/api/v1/auth/register",
        json={
            "name": "Normal User",
            "email": "user@images.example.com",
            "password": "password123",
            "password_confirmation": "password123",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["access_token"]


# ─── Tests ───────────────────────────────────────────────────────────────────


async def test_upload_image_returns_201(img_client, admin_token):
    mock_s3 = MagicMock()
    with patch("app.services.image_upload.boto3.client", return_value=mock_s3):
        resp = await img_client.post(
            "/api/v1/admin/images/upload?type=products",
            files={"file": ("test.jpg", b"fake-image-content", "image/jpeg")},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
    assert resp.status_code == 201
    data = resp.json()
    assert "path" in data
    assert "url" in data
    assert data["path"].startswith("products/")


async def test_upload_image_for_categories(img_client, admin_token):
    mock_s3 = MagicMock()
    with patch("app.services.image_upload.boto3.client", return_value=mock_s3):
        resp = await img_client.post(
            "/api/v1/admin/images/upload?type=categories",
            files={"file": ("test.png", b"fake-png-content", "image/png")},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
    assert resp.status_code == 201
    assert resp.json()["path"].startswith("categories/")


async def test_upload_image_invalid_mime_returns_422(img_client, admin_token):
    resp = await img_client.post(
        "/api/v1/admin/images/upload?type=products",
        files={"file": ("test.pdf", b"pdf-content", "application/pdf")},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 422


async def test_upload_image_too_large_returns_422(img_client, admin_token):
    large_content = b"x" * (5 * 1024 * 1024 + 1)
    resp = await img_client.post(
        "/api/v1/admin/images/upload?type=products",
        files={"file": ("big.jpg", large_content, "image/jpeg")},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 422


async def test_upload_image_401_without_token(img_client):
    resp = await img_client.post(
        "/api/v1/admin/images/upload?type=products",
        files={"file": ("test.jpg", b"data", "image/jpeg")},
    )
    assert resp.status_code == 401


async def test_upload_image_403_for_non_admin(img_client, user_token):
    resp = await img_client.post(
        "/api/v1/admin/images/upload?type=products",
        files={"file": ("test.jpg", b"data", "image/jpeg")},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp.status_code == 403
