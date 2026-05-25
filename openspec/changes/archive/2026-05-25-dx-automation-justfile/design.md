## Context

The project currently has no standardized way to bootstrap a local development environment. Developers must manually copy `.env.example` to `.env`, hunt for `changethis` placeholders, generate cryptographic secrets, and start Docker containers — steps that are undocumented and error-prone. A `Justfile` provides a single discoverable interface for all local workflows, consistent with the project's Docker-first development model.

## Goals / Non-Goals

**Goals:**
- One-command local environment bootstrap (`just setup`)
- Idempotent secret generation (safe to re-run without overwriting valid secrets)
- Standardized wrappers for test, lint, format, migration, and container commands
- Keep the `Justfile` recipes thin — delegate logic to a dedicated script

**Non-Goals:**
- CI/CD integration (pipelines have their own mechanism)
- Production deployment orchestration
- Cross-platform Windows support (macOS/Linux only; project is Docker-based)

## Decisions

### 1. Justfile over Makefile

**Decision**: Use `just` (the `just` command runner) rather than `make`.

**Why**: `just` has no concept of file targets (avoids accidental no-op behavior), supports typed arguments for recipes like `db-makemigrations`, has cleaner syntax, and is purpose-built for running commands rather than build systems.

**Alternative**: `make` is universally available without installation. Rejected because it requires `.PHONY` declarations, has shell quoting quirks, and treats recipe names as file targets by default.

### 2. Dedicated `scripts/setup-env.sh` for env bootstrap logic

**Decision**: Extract all `.env` generation logic into `scripts/setup-env.sh`; the `just setup` recipe just calls this script.

**Why**: Shell logic (loops, sed substitutions, conditionals) embedded directly in Justfile recipes is hard to read and test. A separate script is independently testable, re-usable, and keeps recipes one-liners.

**Alternative**: Inline the logic directly in the `Justfile`. Rejected due to readability and maintainability concerns as logic grows.

### 3. `openssl rand -hex 32` for secret generation

**Decision**: Use `openssl rand -hex 32` to generate secrets, not Python's `secrets` module.

**Why**: `openssl` is available in the base OS on macOS and in the backend container. No Python interpreter invocation needed at bootstrap time (before containers exist).

**Alternative**: `python3 -c "import secrets; print(secrets.token_hex(32))"`. Rejected because it requires Python to be installed locally; `openssl` is a more reliable baseline.

### 4. Idempotency via placeholder detection

**Decision**: The setup script only replaces values that still equal `changethis` (the default placeholder). If a key already has a different value, it is left untouched.

**Why**: Prevents accidental credential rotation on re-run. A developer who manually set a custom `POSTGRES_PASSWORD` will not have it overwritten.

**Implementation**: `sed` replacement conditioned on `grep` matching the placeholder string before replacing.

## Risks / Trade-offs

- **`just` not installed** → Developer sees a clear `command not found` error. Mitigation: add `just` to `docs/` or README installation prerequisites.
- **`openssl` not available** → Unlikely on macOS; fallback is Python one-liner. Mitigation: script can detect and fall back automatically.
- **`.env.example` drift** → If new `changethis` keys are added to `.env.example` but `setup-env.sh` doesn't know about them, they won't be auto-generated. Mitigation: script reads all `changethis` values dynamically from the `.env` file rather than hardcoding key names.

## Migration Plan

1. Add `Justfile` and `scripts/setup-env.sh` to the repository root.
2. No changes to existing code paths, containers, or CI configuration.
3. No rollback needed — both files are additive only.
4. `just setup` uses `docker compose up --build -d` rather than bare `docker compose up -d` because backend/frontend images are not published to a registry and must be built locally on first run.

## Open Questions

- None. All decisions resolved by ticket requirements and constraints above.
