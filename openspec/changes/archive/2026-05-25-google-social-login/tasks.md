## 1. Configuration

- [x] 1.1 Add `GOOGLE_CLIENT_ID: str` and `GOOGLE_CLIENT_SECRET: str` fields to `Settings` in `backend/app/core/config.py`
- [x] 1.2 Add `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` entries (with placeholder values) to `.env.example`

## 2. Database Schema

- [x] 2.1 Change `hashed_password` field in the `User` SQLModel class (`backend/app/models.py`) from `str` to `str | None` with `default=None`
- [x] 2.2 Generate Alembic migration to make the `user.hashed_password` column nullable (`ALTER COLUMN hashed_password DROP NOT NULL`)

## 3. Existing Auth Guard

- [x] 3.1 In `POST /api/v1/login/access-token` (`backend/app/api/routes/login.py`), add an early check: if the authenticated user's `hashed_password` is `None`, return HTTP 400 with message indicating the account requires Google login

## 4. Google OAuth Router

- [x] 4.1 Create `backend/app/api/routes/google_auth.py` with an APIRouter tagged `google-auth`
- [x] 4.2 Implement `GET /auth/google/login`: generate `state` via `secrets.token_urlsafe(32)`, build Google authorization URL with scopes `openid email profile`, set `oauth_state` cookie, return HTTP 302 redirect
- [x] 4.3 Implement `GET /auth/google/callback`: validate `state` vs `oauth_state` cookie (HTTP 400 on mismatch or missing cookie), delete the `oauth_state` cookie, exchange `code` for Google access token via `httpx`, fetch userinfo from `https://www.googleapis.com/oauth2/v3/userinfo`, reject if `email_verified` is not `true`
- [x] 4.4 In the callback handler, implement user provisioning: call `crud.get_user_by_email`; if not found, create new `User` with `is_active=True`, `is_superuser=False`, `hashed_password=None`, and Google `name` as `full_name`
- [x] 4.5 In the callback handler, issue native JWT using `security.create_access_token` and redirect to `{settings.FRONTEND_HOST}/auth/callback?access_token=<jwt>`

## 5. Router Registration

- [x] 5.1 Import and include the `google_auth` router in `backend/app/api/main.py` under the `/api/v1/auth` prefix

## 6. Tests

- [x] 6.1 Create `backend/app/tests/api/routes/test_google_auth.py`
- [x] 6.2 Write test: `GET /auth/google/login` returns 302 with Google `Location` header and sets `oauth_state` cookie
- [x] 6.3 Write test: callback with valid `code` + matching `state` and no existing user → creates new user and redirects with JWT
- [x] 6.4 Write test: callback with valid `code` + matching `state` and existing user → no new user created, redirects with JWT
- [x] 6.5 Write test: callback with `state` mismatch → HTTP 400, no DB write
- [x] 6.6 Write test: callback with missing `oauth_state` cookie → HTTP 400
- [x] 6.7 Write test: callback where Google returns `email_verified: false` → HTTP 400, no user provisioned
- [x] 6.8 Write test: `POST /login/access-token` for an OAuth-only user (`hashed_password=None`) → HTTP 400
