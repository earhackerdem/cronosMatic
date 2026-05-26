## Why

The platform currently only supports email/password login, creating friction for new users who expect single-click social sign-in. Adding Google OAuth 2.0 reduces onboarding drop-off by letting users register and authenticate with their existing Google account, with zero additional credentials to manage.

## What Changes

- Add `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` to `.env.example` and the `Settings` pydantic-settings class.
- Add a new `GET /api/v1/auth/google/login` endpoint that returns (or redirects to) the Google authorization URL.
- Add a new `GET /api/v1/auth/google/callback` endpoint that exchanges the authorization code for a Google access token, fetches the user's email and name, provisions or retrieves the user, and returns the native application JWT.
- Make `hashed_password` nullable on the `User` database model (via Alembic migration) to support OAuth-only accounts.
- Add a new `UserCreateOAuth` schema for provisioning Google users without a local password.
- Add unit tests for both new endpoints, mocking all HTTP calls to Google's API.

## Capabilities

### New Capabilities

- `google-oauth`: Google OAuth 2.0 login and callback endpoints — authorization URL generation, authorization-code exchange, user provisioning/lookup, and native JWT issuance.

### Modified Capabilities

- (none — existing email/password flow is untouched)

## Impact

- **Backend routes**: new file `backend/app/api/routes/google_auth.py`; router registered in `backend/app/api/main.py`.
- **Config**: `backend/app/core/config.py` gains `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` fields; `.env.example` updated accordingly.
- **Model / DB**: `User.hashed_password` becomes `str | None`; new Alembic migration required.
- **CRUD**: new helper `crud.get_or_create_google_user()` (or inline logic in the route) using existing `crud.get_user_by_email`.
- **Dependencies**: `httpx` (already available in the Tiangolo template) used for OAuth token exchange and Google People API calls; no additional OAuth library needed.
- **Tests**: new test module `backend/app/tests/api/routes/test_google_auth.py`; uses `pytest-mock` / `respx` to stub Google API calls.
- **CORS / redirects**: callback may redirect to `FRONTEND_HOST` with JWT in a query param or short-lived cookie; no CORS changes required for server-side redirect.
