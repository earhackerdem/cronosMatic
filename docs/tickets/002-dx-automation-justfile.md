# Ticket 002: Developer Experience (DX) Automation with Justfile

## 1. Objective
Implement a `Justfile` to standardize and automate local development workflows, specifically focusing on a one-click `just setup` command that handles environment variable configuration and container orchestration.

## 2. Context
Currently, setting up the project requires manual intervention to copy environment variables, generate secure cryptographic keys (replacing placeholder `changethis` values), and manage Docker containers. Introducing a `Justfile` will eliminate manual overhead, reduce onboarding friction, and provide a unified interface for testing, linting, and database management.

## 3. Acceptance Criteria (AC)
- [ ] **AC1:** A `Justfile` is created at the root of the repository.
- [ ] **AC2:** The command `just setup` is implemented. It must perform the following sequence:
    - Check if an `.env` file exists; if not, create it from `.env.example` (or the default template).
    - Automatically generate secure random strings (e.g., using `openssl rand -hex 32` or a python script) to replace the `changethis` values for `SECRET_KEY`, `FIRST_SUPERUSER_PASSWORD`, and `POSTGRES_PASSWORD` in the `.env` file.
    - Ensure the secret generation is idempotent (it must NOT overwrite existing secure keys if the command is run twice).
- [ ] **AC3:** The `just setup` command must conclude by executing `docker compose up -d` (or equivalent) to build and start the containers.
- [ ] **AC4:** The `Justfile` must include a `just test` recipe that runs the test suite inside the backend container (incorporating the coverage configurations established in Ticket 001).
- [ ] **AC5:** The `Justfile` must include additional utility recipes:
    - `lint`: Runs standard linters (e.g., ruff).
    - `format`: Runs code formatters.
    - `db-makemigrations <message>`: Wrapper for Alembic revision generation.
    - `db-migrate`: Wrapper for Alembic upgrade head.
    - `logs`: Tails docker compose logs.
    - `down`: Stops and removes containers.

## 4. Implementation Notes
- Consider creating a small Bash or Python script in a `scripts/` directory specifically for the `.env` generation logic (AC2) and calling that script from the `Justfile` to keep the recipes clean.
- Ensure cross-platform compatibility where possible, leveraging the tools already present in the Tiangolo backend container if local dependencies are missing.