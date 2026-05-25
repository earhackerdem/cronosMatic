## Why

Setting up the project requires multiple manual steps: copying `.env` files, generating cryptographic secrets to replace placeholder values, and starting Docker containers — each error-prone and undocumented. A `Justfile` at the repo root eliminates this friction and provides a single, discoverable interface for all local development workflows.

## What Changes

- Add a `Justfile` at the repository root with standard developer workflow recipes.
- Add a `scripts/setup-env.sh` script (or equivalent) that handles `.env` generation and idempotent secret injection.
- `just setup`: bootstraps the full local environment (`.env` creation, secret generation, container startup) in one command.
- `just test`: runs the test suite inside the backend container with coverage (as configured in Ticket 001).
- `just lint` / `just format`: runs `ruff` for linting and formatting.
- `just db-makemigrations <message>` / `just db-migrate`: Alembic wrappers for revision generation and upgrade head.
- `just logs` / `just down`: Docker Compose log tailing and container teardown.

## Capabilities

### New Capabilities

- `justfile-dx`: Developer workflow automation via a root-level `Justfile` — environment bootstrap, testing, linting, formatting, database migrations, and container management.

### Modified Capabilities

## Impact

- **Files added**: `Justfile` (root), `scripts/setup-env.sh` (or `.py`)
- **Files read**: `.env.example`, `compose.yml`, `backend/scripts/test.sh`
- **Dependencies**: `just` CLI must be installed locally; `openssl` used for key generation
- **No breaking changes** to existing code or APIs
