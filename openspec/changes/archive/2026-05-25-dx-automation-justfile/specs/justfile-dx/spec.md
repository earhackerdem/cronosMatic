## ADDED Requirements

### Requirement: Justfile exists at repository root
A `Justfile` SHALL exist at the root of the repository and be executable via the `just` command runner.

#### Scenario: Justfile is present
- **WHEN** a developer clones the repository
- **THEN** a `Justfile` exists at the root and `just --list` displays all available recipes

---

### Requirement: `just setup` bootstraps local environment
The `just setup` command SHALL perform environment bootstrap in this sequence: (1) copy `.env.example` to `.env` if `.env` does not exist, (2) generate secure random secrets to replace all `changethis` placeholder values, (3) start containers with `docker compose up -d`.

#### Scenario: First-time setup on clean clone
- **WHEN** no `.env` file exists and developer runs `just setup`
- **THEN** a `.env` file is created from `.env.example`, all `changethis` values are replaced with cryptographically secure random strings, and Docker containers start in detached mode

#### Scenario: `.env` already exists
- **WHEN** a `.env` file already exists and developer runs `just setup`
- **THEN** the existing `.env` file is NOT overwritten or replaced

---

### Requirement: Secret generation is idempotent
The setup script SHALL NOT overwrite `.env` values that have already been set to a non-placeholder value.

#### Scenario: Re-running setup with existing secrets
- **WHEN** `just setup` is run a second time on a project where secrets have already been generated
- **THEN** the existing secret values in `.env` remain unchanged

#### Scenario: Partial secrets (some still have placeholder)
- **WHEN** `.env` contains a mix of generated secrets and remaining `changethis` placeholders
- **THEN** only the `changethis` placeholder values are replaced; existing generated values are preserved

---

### Requirement: `just test` runs the backend test suite
The `just test` recipe SHALL execute the test suite inside the backend container, incorporating coverage reporting as configured by the test infrastructure.

#### Scenario: Running tests
- **WHEN** developer runs `just test`
- **THEN** tests execute inside the `backend` container and produce coverage output

---

### Requirement: `just lint` runs ruff linter
The `just lint` recipe SHALL run `ruff check` on the backend source code.

#### Scenario: Running linter
- **WHEN** developer runs `just lint`
- **THEN** `ruff check` runs on the backend code and outputs any violations

---

### Requirement: `just format` runs ruff formatter
The `just format` recipe SHALL run `ruff format` on the backend source code.

#### Scenario: Running formatter
- **WHEN** developer runs `just format`
- **THEN** `ruff format` runs and reformats source files in place

---

### Requirement: `just db-makemigrations` generates Alembic revision
The `just db-makemigrations` recipe SHALL accept a message argument and run `alembic revision --autogenerate` inside the backend container.

#### Scenario: Generating a migration
- **WHEN** developer runs `just db-makemigrations "add user table"`
- **THEN** Alembic generates a new migration file with the provided message as its description

---

### Requirement: `just db-migrate` applies pending migrations
The `just db-migrate` recipe SHALL run `alembic upgrade head` inside the backend container.

#### Scenario: Applying migrations
- **WHEN** developer runs `just db-migrate`
- **THEN** all pending Alembic migrations are applied to the database

---

### Requirement: `just logs` tails Docker Compose logs
The `just logs` recipe SHALL run `docker compose logs -f` to stream logs from all services.

#### Scenario: Viewing logs
- **WHEN** developer runs `just logs`
- **THEN** Docker Compose streams logs from all running services in follow mode

---

### Requirement: `just down` stops and removes containers
The `just down` recipe SHALL run `docker compose down` to stop and remove all project containers.

#### Scenario: Tearing down environment
- **WHEN** developer runs `just down`
- **THEN** all project containers are stopped and removed
