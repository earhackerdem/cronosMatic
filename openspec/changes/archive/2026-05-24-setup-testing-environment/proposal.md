## Why

Running `pytest` currently wipes all records from the development database on teardown, because tests share the same PostgreSQL instance as the dev environment. This must be resolved before product development begins to avoid data loss during routine test runs.

## What Changes

- Add a dedicated `app_test_db` PostgreSQL database initialized automatically via Docker (`/docker-entrypoint-initdb.d/`)
- Update `backend/tests/conftest.py` to connect to `app_test_db` when running tests, leaving the dev DB untouched
- Replace `coverage run -m pytest` with `pytest-cov` plugin flags (`--cov-report=term-missing --cov-report=html`) in `backend/scripts/test.sh`
- Add `pytest-cov` to `backend/pyproject.toml` dev dependencies
- Add `htmlcov/` to `.gitignore`

## Capabilities

### New Capabilities

- `test-db-isolation`: Isolated PostgreSQL test database that is automatically provisioned by Docker and used exclusively during test sessions, with zero impact on the dev database
- `test-coverage-reporting`: pytest-cov integration that produces a terminal missing-lines report and an HTML coverage report on every test run

### Modified Capabilities

<!-- No existing spec-level behavior changes -->

## Impact

- `compose.yml` — PostgreSQL service gets a bind-mount for the init SQL script
- `backend/pyproject.toml` — `pytest-cov` added to `[dependency-groups] dev`
- `backend/tests/conftest.py` — engine/session wired to `app_test_db` via `POSTGRES_DB` override or separate DSN
- `backend/scripts/test.sh` — replaced `coverage run` invocation with `pytest --cov` flags
- `.gitignore` — `htmlcov/` entry added
