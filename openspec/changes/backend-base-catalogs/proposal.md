## Why

The `Product` (Watch) entity requires normalised dictionary tables for faceted search and strict data integrity. Without these foundational catalog tables in place, the product model cannot be built — they are hard blockers for Phase 2 development.

## What Changes

- Add four new SQLModel table classes: `Movement`, `CaseMaterial`, `TargetGender`, `WatchStyle`, each with `id` (UUID), `name` (unique, indexed), and optional `description`.
- Add corresponding Pydantic schemas (`Create`, `Read`, `Update`) for each entity.
- Generate and apply an Alembic migration for all four tables.
- Expose protected CRUD endpoints (Create, Read all, Read one, Update, Delete) for each catalog under `/api/v1/catalogs/`.
- Add pytest integration tests covering all endpoints against the isolated test database (`app_test_db`).

## Capabilities

### New Capabilities

- `catalog-crud`: RESTful CRUD API for the four base watch catalog entities (Movement, CaseMaterial, TargetGender, WatchStyle), protected by admin authentication, backed by normalised database tables.

### Modified Capabilities

<!-- none -->

## Impact

- `backend/app/models.py` — four new model + schema classes added
- `backend/app/api/routes/catalogs.py` — new router file (all four catalogs)
- `backend/app/api/main.py` — router registration
- `backend/alembic/versions/` — new migration file
- `backend/app/tests/api/routes/test_catalogs.py` — new test file
