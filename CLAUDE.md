# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

E-commerce backend for watches (CronosMatic). FastAPI + SQLAlchemy 2.0 async + PostgreSQL + Celery/Redis. Python 3.12+, Pydantic v2, Alembic migrations. Frontend is React 19 + TypeScript + Vite.

## Common Commands

```bash
# Docker
make up              # Start all services
make down            # Stop all services
make build           # Rebuild images
make clean           # Stop services and remove volumes

# Database
make db-migrate                    # Run Alembic migrations
make db-revision MSG="description" # Create new migration

# Backend tests (requires running DB)
make test-back                                          # Run all backend tests
make test-back FILE=tests/test_health.py                # Single test file
make test-back FILE=tests/test_health.py ARGS="-k test_name -v"  # Single test
make test-back-cov                                      # Tests with coverage report

# Frontend tests
make test-front      # Run frontend tests (vitest)

# Linting & formatting
make lint-back       # Backend lint + format check
make format-back     # Backend auto-format
cd frontend && npm run lint          # Frontend lint
```

## Architecture

### Backend (`backend/app/`)

Uses a **layered domain architecture** with clear separation:

1. **Domain layer** (`domain/<entity>/`) — Pure Python dataclasses as entities + repository interfaces (Python `Protocol`). No framework dependencies.
2. **Repository layer** (`repositories/`) — Concrete SQLAlchemy implementations of domain repository interfaces. Handles mapping between domain entities and SQLAlchemy models (`_to_domain` / `_to_model`).
3. **Service layer** (`services/`) — Business logic. Depends on repository interfaces, not implementations. Raises domain-specific exceptions (e.g., `CategoryConflictError`).
4. **API layer** (`api/routers/`) — FastAPI route handlers. Uses `Depends()` to wire services with concrete repositories. Catches service exceptions and maps to HTTP errors.
5. **Models** (`models/`) — SQLAlchemy ORM models (DB schema).
6. **Schemas** (`schemas/`) — Pydantic v2 request/response schemas.

**Dependency flow:** Router → Service → Repository Interface ← Concrete Repository → SQLAlchemy Model

**DI wiring pattern** (in each router file):
```python
async def get_category_service(session=Depends(get_db_session)) -> CategoryService:
    repository = CategoryRepository(session)
    return CategoryService(repository)
```

### Key Infrastructure

- `app/config.py` — `Settings` with `env_prefix="BACKEND_"`. For env vars without this prefix (e.g., `DATABASE_URL`), use `validation_alias`.
- `app/db/engine.py` — Async engine + session factory + `get_db_session` dependency.
- `app/main.py` — FastAPI app, CORS middleware, lifespan (engine dispose).
- `app/api/main.py` — Central router aggregation.
- Migrations dir: `backend/alembic/`.
- Package manager: `uv` (not pip). Use `uv add <package>` to add dependencies.
- Tests use `pytest-asyncio` with `asyncio_mode = "auto"` and `httpx.AsyncClient` with `ASGITransport`.

## Ticket Implementation Rule

When implementing a ticket, **always check `docs/infra-gaps.md`** for infrastructure gaps. Each ticket session must:

1. **Read the ticket** from `docs/tickets/XX-name.md`
2. **Check infra gaps** for that ticket number in `docs/infra-gaps.md`
3. **Resolve infra gaps first**: add missing env vars to `.env.example`, `.env`, `docker-compose.yml`; add missing Python deps to `pyproject.toml`; add/update Docker services
4. **Implement the ticket** following the spec
5. **Update `Makefile`** if new commands are needed
6. **Run tests** before considering the ticket done
7. **Mark resolved infra gaps** as done in `docs/infra-gaps.md`

## Code Conventions

- **Async everything**: SQLAlchemy 2.0 async with `AsyncSession`. Never use sync session in FastAPI handlers.
- **HTTP status codes**: 401 auth failures, 404 not-found/ownership, 422 only for Pydantic validation errors.
- **`HTTPException.detail`**: always a string, never a dict.
- **Query params**: always snake_case.
- **`updated_at`**: use SQLAlchemy `onupdate=func.now()`, not DB triggers.
- **DELETE responses**: 204 No Content (except cart endpoints which return the updated cart).
- **i18n fields**: Stored as `dict[str, str]` JSON (e.g., `{"en": "Pocket", "es": "Bolsillo"}`).
- **Soft deletes**: Use `deleted_at` timestamp, filter with `.where(Model.deleted_at.is_(None))`.
- **Testing strategy**: Only write endpoint/integration tests (`httpx.AsyncClient` against real DB). No unit tests for domain entities, repositories, or services. The API tests cover all layers end-to-end.
