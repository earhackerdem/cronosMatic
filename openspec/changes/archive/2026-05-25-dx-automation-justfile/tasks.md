## 1. Environment Bootstrap Script

- [x] 1.1 Create `scripts/setup-env.sh` that copies `.env.example` to `.env` if `.env` does not exist
- [x] 1.2 Add logic to `scripts/setup-env.sh` to replace all `changethis` placeholder values with `openssl rand -hex 32` output — only replacing values that are still equal to `changethis`
- [x] 1.3 Make `scripts/setup-env.sh` executable (`chmod +x`)

## 2. Justfile — Bootstrap Recipes

- [x] 2.1 Create `Justfile` at repository root with a default recipe that lists all available commands
- [x] 2.2 Add `setup` recipe: calls `scripts/setup-env.sh` then runs `docker compose up -d`

## 3. Justfile — Development Workflow Recipes

- [x] 3.1 Add `test` recipe: runs the test suite inside the backend container (via `docker compose exec backend` or equivalent, using the existing `scripts/test.sh`)
- [x] 3.2 Add `lint` recipe: runs `ruff check` inside the backend container
- [x] 3.3 Add `format` recipe: runs `ruff format` inside the backend container

## 4. Justfile — Database Recipes

- [x] 4.1 Add `db-makemigrations message` recipe: runs `alembic revision --autogenerate -m "$message"` inside the backend container
- [x] 4.2 Add `db-migrate` recipe: runs `alembic upgrade head` inside the backend container

## 5. Justfile — Container Utility Recipes

- [x] 5.1 Add `logs` recipe: runs `docker compose logs -f`
- [x] 5.2 Add `down` recipe: runs `docker compose down`

## 6. Verification

- [x] 6.1 Run `just --list` and confirm all recipes are listed
- [x] 6.2 Run `just setup` on a clean clone (no `.env`) and verify `.env` is created with secrets filled in and containers start
- [x] 6.3 Run `just setup` a second time and verify existing `.env` secrets are not overwritten
- [x] 6.4 Run `just test` and verify tests run inside the container with coverage output
- [x] 6.5 Run `just lint` and `just format` and verify they execute without errors
