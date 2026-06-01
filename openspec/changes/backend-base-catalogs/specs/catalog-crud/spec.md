## ADDED Requirements

### Requirement: Catalog entity models exist in the database
Each of the four catalog types (Movement, CaseMaterial, TargetGender, WatchStyle) SHALL have a corresponding database table created via Alembic migration. Each table SHALL contain: `id` (UUID, primary key), `name` (String, unique, indexed, max 255 chars), and `description` (String, optional, max 500 chars).

#### Scenario: Migration creates all four tables
- **WHEN** `alembic upgrade head` is executed on a clean database
- **THEN** tables `movement`, `casematerial`, `targetgender`, and `watchstyle` are present with the correct columns and constraints

#### Scenario: Name uniqueness is enforced at the database level
- **WHEN** two records with the same `name` are inserted into any catalog table
- **THEN** the database raises an integrity error

### Requirement: SQLModel classes and Pydantic schemas are defined for each catalog entity
Each catalog entity SHALL have a `Base` SQLModel class, a `Create` schema, an `Update` schema (all fields optional), and a `Public` (read) schema. The `Public` schema SHALL include `id` and `name`; `description` is optional in all schemas.

#### Scenario: Create schema validates required name field
- **WHEN** a request is made to create a catalog entry without a `name`
- **THEN** the API returns HTTP 422 Unprocessable Entity

#### Scenario: Update schema accepts partial data
- **WHEN** an update request is made with only `description` and no `name`
- **THEN** the API updates only `description` and leaves `name` unchanged

### Requirement: Admin-only CRUD endpoints exist for all four catalog types
The system SHALL expose five endpoints per catalog entity under `/api/v1/catalogs/{entity}/`, all requiring `is_superuser=True`: POST (create), GET / (list all), GET /{id} (read one), PUT /{id} (update), DELETE /{id} (delete). The four entity slugs are: `movements`, `case-materials`, `target-genders`, `watch-styles`.

#### Scenario: Unauthenticated request is rejected
- **WHEN** any catalog endpoint is called without a valid JWT token
- **THEN** the API returns HTTP 401 Unauthorized

#### Scenario: Non-admin authenticated request is rejected
- **WHEN** any catalog endpoint is called with a valid JWT token for a non-superuser
- **THEN** the API returns HTTP 403 Forbidden

#### Scenario: Admin creates a catalog entry
- **WHEN** a superuser sends POST `/api/v1/catalogs/movements/` with `{"name": "Automatic"}`
- **THEN** the API returns HTTP 200 with the created entry including its `id` and `name`

#### Scenario: Admin lists all entries for a catalog
- **WHEN** a superuser sends GET `/api/v1/catalogs/movements/`
- **THEN** the API returns HTTP 200 with a JSON object containing `data` (array) and `count` (integer)

#### Scenario: Admin reads a single catalog entry
- **WHEN** a superuser sends GET `/api/v1/catalogs/movements/{id}` for an existing entry
- **THEN** the API returns HTTP 200 with the entry's `id`, `name`, and `description`

#### Scenario: Read one returns 404 for unknown ID
- **WHEN** a superuser sends GET `/api/v1/catalogs/movements/{non-existent-id}`
- **THEN** the API returns HTTP 404 Not Found

#### Scenario: Admin updates a catalog entry
- **WHEN** a superuser sends PUT `/api/v1/catalogs/movements/{id}` with `{"name": "Manual"}`
- **THEN** the API returns HTTP 200 with the updated entry

#### Scenario: Update returns 404 for unknown ID
- **WHEN** a superuser sends PUT `/api/v1/catalogs/movements/{non-existent-id}`
- **THEN** the API returns HTTP 404 Not Found

#### Scenario: Admin deletes a catalog entry
- **WHEN** a superuser sends DELETE `/api/v1/catalogs/movements/{id}` for an existing entry
- **THEN** the API returns HTTP 200 with a confirmation message and the entry is removed

#### Scenario: Delete returns 404 for unknown ID
- **WHEN** a superuser sends DELETE `/api/v1/catalogs/movements/{non-existent-id}`
- **THEN** the API returns HTTP 404 Not Found

### Requirement: Delete endpoint handles future foreign key constraint violations gracefully
When a catalog entry is referenced by another table (e.g., a future `Product` table), the DELETE endpoint SHALL return HTTP 409 Conflict instead of a 500 Internal Server Error.

#### Scenario: Delete fails due to FK constraint
- **WHEN** a superuser attempts to DELETE a catalog entry that is referenced by another table
- **THEN** the API returns HTTP 409 Conflict with a descriptive error message

### Requirement: Integration tests cover all CRUD endpoints for all four catalog types
The test suite SHALL include pytest tests for every endpoint × entity combination, running against the isolated `app_test_db`. Tests SHALL assert correct status codes, response shapes, and error cases (404, 403, 422).

#### Scenario: All catalog tests pass in isolation
- **WHEN** the test suite is run with `pytest backend/tests/api/routes/test_catalogs.py`
- **THEN** all tests pass without touching the development database
