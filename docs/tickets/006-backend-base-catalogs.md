# Ticket 005: Backend - Base Catalogs Models and CRUD (Phase 1)

## 1. Objective
Implement the database models (SQLModel) and the corresponding RESTful CRUD endpoints (FastAPI) for the base watch catalogs: Movement, Case Material, Target Gender, and Watch Style.

## 2. Context
Before building the complex `Product` (Watch) entity, the system requires foundational dictionary tables to support the faceted search and strict data integrity. These entities share a simple, uniform structure. Grouping them in a single backend ticket is efficient for an AI-driven workflow since the implementation pattern is identical across all four.

## 3. Acceptance Criteria (AC)
- [ ] **AC1:** Create SQLModel classes representing the database tables for `Movement`, `CaseMaterial`, `TargetGender`, and `WatchStyle`. Each model should contain at least an `id` (UUID or Integer) and a `name` (String, unique, indexed). Optional: a `description` field.
- [ ] **AC2:** Create the corresponding Pydantic schemas for data validation (`Create`, `Read`, `Update` schemas for each entity).
- [ ] **AC3:** Generate and apply the Alembic database migration for these new tables.
- [ ] **AC4:** Implement protected API routes (requiring admin authentication) for standard CRUD operations (Create, Read all, Read one, Update, Delete) for each of the four catalogs under the `/api/v1/` prefix.
- [ ] **AC5:** Write unit tests using `pytest` for the new endpoints, ensuring they correctly interact with the isolated testing database (`app_test_db`).

## 4. Implementation Notes
- Follow the existing repository structure (e.g., place models in `backend/app/models.py` or a dedicated `models/` directory, and APIs in `backend/app/api/routes/`).
- Ensure the Delete endpoints handle potential future foreign key constraints gracefully (even if the `Product` table doesn't exist yet, standard HTTP 400 responses should be mapped for integrity errors).