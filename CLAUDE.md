# CronosMatic — Project Rules

## Project Overview
- E-commerce backend for watches (CronosMatic)
- FastAPI + SQLAlchemy 2.0 async + PostgreSQL + Celery/Redis
- Python 3.12+, Pydantic v2, Alembic migrations
- Backend lives in `backend/`, uses `uv` for dependency management
- Migrations dir is `backend/migrations/` (NOT `alembic/`)

## Key Files
- `backend/pyproject.toml` — dependencies and config
- `backend/app/config.py` — Settings with `env_prefix = "BACKEND_"` (note: `DATABASE_URL` uses `validation_alias` to bypass prefix)
- `docker-compose.yml` — db, pgadmin, backend, frontend (missing Redis, Celery — added per ticket)
- `.env.example` / `.env` — env vars (expanded per ticket as needed)
- `Makefile` — dev commands (up, down, migrate, test)
- `docs/tickets/00-09` — implementation tickets
- `docs/infra-gaps.md` — per-ticket infrastructure gaps to resolve during implementation

## Infra Notes
- `Settings` uses `env_prefix="BACKEND_"` — new env vars need `validation_alias` if they don't follow this prefix
- Dockerfile copies `migrations/` not `alembic/`
- Frontend port 4200, framework TBD (Angular or React — needs clarification)
- CORS currently uses `allow_headers=["*"]`, `allow_credentials=True`

## Ticket Implementation Rule

When implementing a ticket, **always check `docs/infra-gaps.md`** for infrastructure gaps that must be resolved as part of that ticket. Each ticket session must:

1. **Read the ticket** from `docs/tickets/XX-name.md`
2. **Check infra gaps** for that ticket number in `docs/infra-gaps.md`
3. **Resolve infra gaps first**: add missing env vars to `.env.example`, `.env`, `docker-compose.yml`; add missing Python deps to `pyproject.toml`; add/update Docker services if needed
4. **Implement the ticket** following the spec
5. **Update `Makefile`** if new commands are needed (e.g., celery worker)
6. **Run tests** before considering the ticket done
7. **Mark resolved infra gaps** as done in `docs/infra-gaps.md`

## Code Conventions

- **Settings**: `backend/app/config.py` uses `env_prefix = "BACKEND_"`. For env vars that don't follow this prefix (e.g., `DATABASE_URL`, `REDIS_URL`), use `validation_alias` on the field.
- **Migrations**: directory is `backend/migrations/`, NOT `alembic/`.
- **Package manager**: `uv` (not pip). Use `uv add <package>` to add dependencies.
- **Async everything**: SQLAlchemy 2.0 async with `AsyncSession`. Never use sync session in FastAPI handlers.
- **HTTP status codes**: 401 auth failures, 404 not-found/ownership, 422 only for Pydantic validation errors.
- **`HTTPException.detail`**: always a string, never a dict.
- **Query params**: always snake_case.
- **`updated_at`**: use SQLAlchemy `onupdate=func.now()`, not DB triggers.
- **DELETE responses**: 204 No Content (except cart endpoints which return the updated cart).
