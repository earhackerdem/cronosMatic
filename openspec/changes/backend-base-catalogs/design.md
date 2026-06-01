## Context

The backend is a FastAPI + SQLModel application. Models live in `backend/app/models.py`, routes in `backend/app/api/routes/` (one file per domain), and the API router is assembled in `backend/app/api/main.py`. Authentication is via JWT; admin protection uses the `get_current_active_superuser` dependency from `backend/app/api/deps.py`.

The four catalog entities (Movement, CaseMaterial, TargetGender, WatchStyle) are pure dictionary tables: no ownership, no relations to other tables yet (the Product entity comes in a later phase).

Tests live in `backend/tests/`, follow the `TestClient` + `conftest.py` fixture pattern, and run against `app_test_db`.

## Goals / Non-Goals

**Goals:**
- Add four catalog SQLModel table models with UUID PK, unique indexed `name`, and optional `description`.
- Add Pydantic schemas (`Create`, `Read`, `Update`) per entity following the existing `Base → Create/Update/Public` pattern.
- Expose a single router file `backend/app/api/routes/catalogs.py` covering all four catalogs under `/api/v1/catalogs/{entity}/`.
- Generate and apply an Alembic migration for all four tables.
- Write pytest integration tests for all CRUD endpoints.

**Non-Goals:**
- Foreign key relations to a `Product` table (Phase 2).
- Soft delete, audit trail, or ordering fields.
- Non-admin read access (catalogs are admin-managed dictionary data).
- Pagination on list endpoints (catalogs are small, bounded sets).

## Decisions

### D1 — Single router file for all four catalogs
**Decision**: Implement all four catalog routers in one file (`catalogs.py`) using a factory function or parametrised approach, rather than four separate files.
**Rationale**: The four entities are structurally identical. A factory avoids copy-paste across four nearly-identical files and keeps the route registration surface minimal (`api_router.include_router(catalogs.router)`). Alternative (four files) adds maintenance overhead for no behavioural difference.

### D2 — URL scheme: `/catalogs/{entity-slug}/`
**Decision**: Use a shared prefix `/catalogs/` with an entity-specific sub-prefix (`/catalogs/movements/`, `/catalogs/case-materials/`, `/catalogs/target-genders/`, `/catalogs/watch-styles/`).
**Rationale**: Groups all catalog CRUD under one discoverable path prefix; consistent with REST conventions for subordinate resource types. Alternative (top-level `/movements/`, etc.) pollutes the root namespace.

### D3 — UUID primary key (not Integer)
**Decision**: Use `uuid.UUID` as the PK for all four catalog tables, matching the existing `User` and `Item` tables.
**Rationale**: Consistency with the rest of the schema; avoids integer sequence coordination issues if data is seeded across environments. The catalog tables are small so UUID overhead is irrelevant.

### D4 — Admin-only for all endpoints (including reads)
**Decision**: All five CRUD endpoints (Create, Read all, Read one, Update, Delete) require `is_superuser=True`.
**Rationale**: The ticket specifies "protected API routes (requiring admin authentication)". Catalog data is seeded/managed by admins, not end users. Public read access is deferred to when the Product API exposes catalog options as part of its response.

### D5 — IntegrityError → HTTP 409 for Delete
**Decision**: Wrap the `session.delete()` call in a try/except for `sqlalchemy.exc.IntegrityError` and raise HTTP 409 Conflict, not 400.
**Rationale**: 409 Conflict is the correct semantic for a constraint violation on an existing resource. The ticket asks for graceful handling of future FK constraints; 409 is the idiomatic REST response.

## Risks / Trade-offs

- [Risk] Four tables created in one migration — if the migration fails mid-way, partial state could require a manual rollback. → **Mitigation**: Alembic wraps each migration in a transaction; all four tables are created atomically.
- [Risk] Factory-pattern router may be harder to navigate for unfamiliar contributors. → **Mitigation**: Each sub-router has explicit tags and docstrings; the factory pattern is documented in the router file header.
- [Trade-off] Admin-only reads means the frontend cannot yet display catalog options to end users for Product filtering. Accepted — public catalog exposure is Phase 2 scope.

## Migration Plan

1. Run `alembic revision --autogenerate -m "add catalog tables"` inside the backend container.
2. Review generated migration for correctness (UUID type, unique constraint on `name`).
3. Apply with `alembic upgrade head`.
4. Rollback: `alembic downgrade -1` drops all four tables.
