## ADDED Requirements

### Requirement: Dedicated test database provisioned by Docker
The PostgreSQL Docker service SHALL automatically create a secondary database (`app_test_db`) on container initialization, without manual intervention.

#### Scenario: First container start provisions test database
- **WHEN** the `db` Docker service starts with a fresh volume
- **THEN** `app_test_db` exists alongside the default dev database

#### Scenario: Test database survives container restarts
- **WHEN** the `db` container is restarted without removing the volume
- **THEN** `app_test_db` is still present and accessible

### Requirement: Test sessions connect to the isolated test database
The test suite SHALL connect exclusively to `app_test_db` during every pytest session, and the dev database SHALL NOT be queried or modified by any test.

#### Scenario: Dev database is untouched after a test run
- **WHEN** `pytest` is executed
- **THEN** no rows are added to or deleted from the dev database

#### Scenario: Test fixtures operate on app_test_db
- **WHEN** the `db` session fixture runs `init_db` and the teardown deletes all rows
- **THEN** those operations execute only against `app_test_db`

### Requirement: Test database connection uses `POSTGRES_DB` override
The test configuration SHALL override `POSTGRES_DB` to `app_test_db` before the SQLAlchemy engine is constructed, so `pydantic-settings` resolves the correct connection URL for the test session.

#### Scenario: Engine URL points to app_test_db during tests
- **WHEN** conftest.py runs before any test
- **THEN** the engine connection string contains `app_test_db` as the database name

#### Scenario: Override does not persist to application settings at runtime
- **WHEN** the application starts normally (not under pytest)
- **THEN** `POSTGRES_DB` resolves to the value from `.env`, not `app_test_db`
