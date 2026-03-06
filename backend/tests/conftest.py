"""Test configuration and fixtures.

Key design decisions:
- Each async test gets its own event loop (asyncio_mode="auto" default).
- Repository tests use a per-test engine to avoid interfering with the app.
- Router integration tests override get_db_session via app.dependency_overrides
  to use a per-test engine+session, ensuring isolation AND no event loop conflicts.
"""
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.db.base import Base
from app.db.engine import get_db_session
from app.main import app

# Import all models so they register with Base.metadata
from app.models import Item  # noqa: F401
from app.models.category import CategoryModel  # noqa: F401
from app.models.refresh_token import RefreshTokenModel  # noqa: F401
from app.models.user import UserModel  # noqa: F401


# ─── Repository integration test fixtures ────────────────────────────────────


@pytest.fixture
async def db_session():
    """Per-test async DB session for repository integration tests.

    Uses a fresh engine per test to avoid event-loop conflicts.
    Truncates auth data after each test.
    """
    engine = create_async_engine(settings.database_url, echo=False)

    # Ensure all tables exist (idempotent)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    # Clean up test data (truncate, not drop)
    async with engine.begin() as conn:
        await conn.execute(
            text("TRUNCATE TABLE refresh_tokens, users RESTART IDENTITY CASCADE")
        )

    await engine.dispose()


# ─── Router / API integration test fixtures ──────────────────────────────────


@pytest.fixture
async def client():
    """HTTP client that overrides DB session with a per-test engine.

    This prevents event-loop conflicts by using a fresh engine per test,
    injected via FastAPI's dependency_overrides mechanism.
    """
    engine = create_async_engine(settings.database_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db_session():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db_session

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()

    # Clean up test data
    async with engine.begin() as conn:
        await conn.execute(
            text("TRUNCATE TABLE refresh_tokens, users RESTART IDENTITY CASCADE")
        )

    await engine.dispose()
