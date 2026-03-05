# Ticket 00: Project Setup

**Priority:** P0 — Blocker for all other tickets  
**Dependencies:** None  
**Estimate:** 1 session

---

## Objective

Create the base project structure for FastAPI with all the necessary infrastructure: PostgreSQL database, Redis, Celery, and AWS S3 configuration.

---

## Technology Stack

| Component | Technology |
|-----------|-----------|
| Framework | FastAPI |
| ORM | SQLAlchemy 2.0 (async) |
| Migrations | Alembic |
| Database | PostgreSQL |
| Task Queue | Celery + Redis |
| Storage | AWS S3 (boto3) |
| Auth | python-jose (JWT) + passlib (hashing) |
| Validation | Pydantic v2 |
| HTTP Client | httpx (for PayPal API) |
| Email | fastapi-mail or similar |
| Testing | pytest + pytest-asyncio + httpx |
| Pagination | fastapi-pagination or custom schema |

---

## Recommended Project Structure

```
app/
├── main.py                    # FastAPI app factory, routers include
├── config.py                  # Settings with pydantic-settings (env vars)
├── database.py                # SQLAlchemy engine, session, Base
├── dependencies.py            # Shared dependencies (get_db, get_current_user)
├── models/                    # SQLAlchemy models
│   ├── __init__.py
│   ├── user.py
│   ├── category.py
│   ├── product.py
│   ├── cart.py
│   ├── cart_item.py
│   ├── order.py
│   ├── order_item.py
│   └── address.py
├── schemas/                   # Pydantic schemas (request/response)
│   ├── __init__.py
│   ├── auth.py
│   ├── category.py
│   ├── product.py
│   ├── cart.py
│   ├── order.py
│   ├── address.py
│   └── pagination.py
├── services/                  # Business logic
│   ├── __init__.py
│   ├── auth_service.py
│   ├── cart_service.py
│   ├── order_service.py
│   ├── address_service.py
│   └── paypal_service.py
├── routers/                   # Route handlers
│   ├── __init__.py
│   ├── auth.py
│   ├── categories.py
│   ├── products.py
│   ├── cart.py
│   ├── orders.py
│   ├── addresses.py
│   ├── payments.py
│   ├── admin/
│   │   ├── __init__.py
│   │   ├── categories.py
│   │   ├── products.py
│   │   └── images.py
│   └── health.py
├── tasks/                     # Celery tasks
│   ├── __init__.py
│   └── email_tasks.py
└── utils/                     # Helpers
    ├── __init__.py
    ├── security.py            # JWT encode/decode, password hash/verify
    ├── pagination.py          # Pagination helper
    └── s3.py                  # S3 upload helper
alembic/                       # Alembic migrations
├── versions/
├── env.py
└── alembic.ini
tests/
├── conftest.py                # Fixtures (db session, client, auth headers)
├── test_auth.py
├── test_categories.py
├── test_products.py
├── test_cart.py
├── test_orders.py
├── test_addresses.py
├── test_payments.py
└── test_admin.py
```

---

## Required Configuration (Environment Variables)

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/cronosmatic

# JWT
JWT_SECRET_KEY=<random-secret>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Redis
REDIS_URL=redis://localhost:6379/0

# AWS S3
AWS_ACCESS_KEY_ID=<key>
AWS_SECRET_ACCESS_KEY=<secret>
AWS_S3_BUCKET_NAME=cronosmatic-images
AWS_S3_REGION=us-east-1

# PayPal
PAYPAL_MODE=sandbox
PAYPAL_CLIENT_ID=<client_id>
PAYPAL_CLIENT_SECRET=<client_secret>
PAYPAL_SIMULATE_PAYMENTS=true

# Email
MAIL_FROM=noreply@cronosmatic.com
MAIL_SERVER=smtp.example.com
MAIL_PORT=587
MAIL_USERNAME=<username>
MAIL_PASSWORD=<password>

# App
APP_ENV=development
APP_DEBUG=true
CORS_ORIGINS=http://localhost:5173
```

---

## Standard Pagination Schema

All paginated endpoints must return this format:

```json
{
  "items": [...],
  "total": 100,
  "page": 1,
  "pages": 10,
  "size": 10
}
```

Query params: `?page=1&size=10`

---

## CORS

Configure CORS to allow:
- Origins: `CORS_ORIGINS` (comma-separated in env var)
- Methods: `GET, POST, PUT, PATCH, DELETE, OPTIONS`
- Headers: `Authorization, Content-Type, X-Session-ID`
- Credentials: `false` (no cookies, JWT only)

---

## Acceptance Criteria

- [ ] `uvicorn app.main:app` starts without errors
- [ ] `GET /api/v1/status` returns `{ "status": "ok", "message": "API is running", "timestamp": "..." }`
- [ ] PostgreSQL connects and Alembic can create migrations
- [ ] Redis connects and Celery worker starts
- [ ] Environment variables load correctly from `.env`
- [ ] CORS allows requests from the React frontend
- [ ] The `X-Session-ID` header passes through CORS without being blocked
- [ ] pytest runs a basic health endpoint test
