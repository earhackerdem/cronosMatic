## Context

The project uses FastAPI + SQLModel + PostgreSQL. Tests run via `pytest` inside the Docker backend container. Currently `conftest.py` builds an `engine` from `app.core.db` which points to `POSTGRES_DB` (the dev database). The teardown fixture deletes all `Item` and `User` rows, wiping dev data on every test run. The backend already ships with `coverage` in dev dependencies and a `backend/scripts/test.sh` that calls `coverage run -m pytest`. The ticket requires switching to `pytest-cov` for a tighter pytest plugin integration and adding a dedicated test database.

## Goals / Non-Goals

**Goals:**
- Provision a second PostgreSQL database (`app_test_db`) automatically when the Docker container starts
- Route all test sessions to `app_test_db` so the dev database is never touched
- Replace the `coverage run` invocation with `pytest --cov` flags for terminal and HTML reports
- Ensure `htmlcov/` is gitignored

**Non-Goals:**
- Separate Docker service for tests — we reuse the existing `db` container
- Changing the test data fixtures or test structure beyond what is needed for isolation
- CI/CD pipeline changes

## Decisions

### D1 — Provision `app_test_db` via `/docker-entrypoint-initdb.d/`

**Decision**: Mount a shell script into `/docker-entrypoint-initdb.d/` on the `db` service that runs `CREATE DATABASE app_test_db` if it does not already exist.

**Why**: The official `postgres` Docker image executes any `.sh` or `.sql` files placed in that directory on first container initialization. This is idiomatic, requires no extra tooling, and runs before any application code.

**Alternative considered**: Create the DB in the `prestart.sh` script — rejected because prestart runs in the backend container and needs a superuser connection, adding unnecessary coupling.

### D2 — Override `POSTGRES_DB` env var in `conftest.py`

**Decision**: In `conftest.py`, before building the test engine, set `os.environ["POSTGRES_DB"]` to `app_test_db` and reconstruct (or override) the SQLAlchemy URL so `pydantic-settings` picks up the test database name.

**Why**: `pydantic-settings` reads `POSTGRES_DB` at import time via `Settings()`. We need to override it before the engine is constructed. The cleanest approach is to set the env var before the `settings` object is instantiated for tests, using a `conftest.py`-level fixture or module-level override that runs before any app import resolves the DB URL.

**Alternative considered**: A separate `.env.test` file — rejected because it requires the test runner to source it explicitly and adds per-developer setup friction.

**Alternative considered**: A second `Settings` subclass — rejected as over-engineering for a single variable change.

### D3 — Switch to `pytest-cov` plugin

**Decision**: Add `pytest-cov` to `[dependency-groups] dev` and update `backend/scripts/test.sh` to call `pytest --cov=app --cov-report=term-missing --cov-report=html` instead of `coverage run -m pytest` + separate `coverage report/html` calls.

**Why**: `pytest-cov` integrates directly as a pytest plugin, enabling coverage collection without a subprocess wrapper. It respects `[tool.coverage.*]` config in `pyproject.toml` and is the standard approach in the ecosystem. The existing `coverage` package remains as a transitive dependency.

## Risks / Trade-offs

- **First-run init only**: `/docker-entrypoint-initdb.d/` scripts run only on a fresh volume. Existing dev environments with a pre-existing volume need `docker compose down -v` once to trigger re-initialization. → Mitigation: document this in the PR description.
- **Env var side-effect timing**: Overriding `POSTGRES_DB` in `conftest.py` before `app.core.db` imports is order-sensitive. If any test module imports `app.core.db` at the top level before conftest runs, the override may be missed. → Mitigation: use a `session`-scoped autouse fixture that asserts the DB name before the first query.
- **`pytest-cov` + `coverage` coexistence**: Having both in dev deps is harmless; `pytest-cov` calls the same `coverage` API under the hood. → No mitigation needed.

## Migration Plan

1. Add init script to repo (`docker/init-test-db.sh`)
2. Bind-mount it in `compose.yml` under the `db` service
3. Update `backend/tests/conftest.py` to override `POSTGRES_DB` before engine construction
4. Add `pytest-cov` to `backend/pyproject.toml`
5. Update `backend/scripts/test.sh`
6. Add `htmlcov/` to `.gitignore`
7. Tear down and recreate local volume: `docker compose down -v && docker compose up -d`

**Rollback**: Remove the bind-mount and revert `conftest.py`; the dev DB is unaffected.

## Open Questions

- Should `app_test_db` be parameterized (e.g., `${POSTGRES_DB}_test`) or hardcoded? Hardcoded for now — simpler and sufficient for a single-environment template.
