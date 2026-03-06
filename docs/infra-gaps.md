# Infrastructure Gaps to Resolve Per Ticket

These gaps exist between tickets and the actual Docker/env/config setup.
Each should be resolved **during the ticket that introduces the dependency**.

## Ticket 00 (Project Setup) ✅ RESOLVED
- ~~Health endpoint is at `GET /health`, ticket says `GET /api/v1/status` — align during setup~~
  - Added `/api/v1` prefix to central router; added `GET /status` endpoint
- ~~Ticket says `alembic/` directory but actual project uses `migrations/` — ticket must match reality~~
  - Resolved: renamed to `alembic/` (Python/Alembic convention)
- ~~CORS: actual code uses `allow_headers=["*"]` and `allow_credentials=True`, ticket says restricted headers and `credentials: false` — decide during setup~~
  - CORS aligned: `credentials=False`, explicit methods and headers
- ~~`.env.example` says "Angular", tickets say "React"~~
  - Fixed to "React"; CORS origins include both Vite (5173) and legacy (4200) ports
- Redis/Celery deferred to Tickets 04/08

## Ticket 01 (Auth) ✅ RESOLVED
- ~~`Settings` class uses `env_prefix = "BACKEND_"`. JWT vars need `BACKEND_JWT_*` naming~~
  - Added `jwt_secret_key`, `jwt_access_token_expire_minutes`, `jwt_refresh_token_expire_days` to Settings
- ~~Add JWT/auth env vars to `.env.example`, `docker-compose.yml` backend service, and `Makefile` commands~~
  - Added to all files including Makefile test commands
- ~~Add `passlib[bcrypt]`, `python-jose[cryptography]` to `pyproject.toml`~~
  - Added via `uv add`; also added `email-validator` for Pydantic EmailStr

## Ticket 03 (Products + Images)
- Add `boto3` to `pyproject.toml`
- Add `AWS_*` env vars to `.env.example` and `docker-compose.yml`

## Ticket 04 (Cart)
- Add `redis` service to `docker-compose.yml`
- Add `REDIS_URL` to `.env.example` and compose backend env
- Add `redis` Python package to `pyproject.toml` (if needed for direct access beyond Celery)

## Ticket 06 (Orders)
- Add `DEFAULT_SHIPPING_COST` to `.env.example` and compose

## Ticket 07 (PayPal)
- Add `httpx` to prod dependencies in `pyproject.toml` (currently only in dev)
- Add `PAYPAL_*`, `PAYMENT_CURRENCY`, `PAYMENT_COUNTRY_CODE` to `.env.example` and compose

## Ticket 08 (Emails + Celery)
- Add `celery-worker` and `celery-beat` services to `docker-compose.yml`
- Both reuse the backend image, just change the CMD
- Add `celery`, `redis`, `fastapi-mail` to `pyproject.toml`
- Add `MAIL_*` env vars to `.env.example` and compose
- Update `Makefile` with celery worker/beat commands
