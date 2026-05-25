## 1. Docker — Provision Test Database

- [x] 1.1 Create `docker/init-test-db.sh` with a `psql` command that creates `app_test_db` if it does not exist
- [x] 1.2 Mount `docker/init-test-db.sh` into `/docker-entrypoint-initdb.d/` on the `db` service in `compose.yml`

## 2. Backend — Test Session Isolation

- [x] 2.1 In `backend/tests/conftest.py`, override `os.environ["POSTGRES_DB"]` to `"app_test_db"` before `app.core.db` is imported, so `pydantic-settings` resolves the test DSN
- [x] 2.2 Rebuild the SQLAlchemy engine inside the `db` fixture using the overridden settings (or pass the test URL explicitly) to confirm the connection targets `app_test_db`
- [x] 2.3 Add an assertion in the `db` fixture that verifies the engine URL contains `app_test_db` before any query runs

## 3. Backend — pytest-cov Integration

- [x] 3.1 Add `pytest-cov` to `[dependency-groups] dev` in `backend/pyproject.toml`
- [x] 3.2 Run `uv sync --group dev` inside the backend container to install the new dependency (update `uv.lock`)
- [x] 3.3 Replace the body of `backend/scripts/test.sh` to use `pytest --cov=app --cov-report=term-missing --cov-report=html tests/` (remove the separate `coverage run`, `coverage report`, and `coverage html` calls)

## 4. Gitignore

- [x] 4.1 Add `htmlcov/` to the root `.gitignore` file

## 5. Verification

- [x] 5.1 Tear down the local Docker volume (`docker compose down -v`) and restart (`docker compose up -d`) to trigger `/docker-entrypoint-initdb.d/` and confirm `app_test_db` is created
- [x] 5.2 Run the full test suite and confirm the dev database rows are unchanged
- [x] 5.3 Confirm `htmlcov/index.html` is generated and terminal shows the missing-lines table
- [x] 5.4 Run `git status` and confirm `htmlcov/` does not appear as untracked
