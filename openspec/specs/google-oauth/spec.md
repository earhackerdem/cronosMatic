# Spec: Google OAuth

## Purpose

Defines requirements for Google social login via OAuth 2.0. Users can authenticate using their Google account, with the system provisioning new users automatically and issuing native JWTs upon successful authentication.

## Requirements

### Requirement: Google OAuth configuration
`GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` SHALL be exposed in `.env.example` and loaded as optional fields (type `str | None`) through the `Settings` pydantic-settings class. When either value is absent or `None`, any Google OAuth endpoint SHALL respond with HTTP 503 rather than crashing at startup — allowing deployments that do not use Google login to continue operating normally.

#### Scenario: Settings loaded with valid Google credentials
- **WHEN** both `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are present in the environment
- **THEN** the `Settings` object SHALL expose them as non-None string attributes

#### Scenario: Google OAuth endpoint called without credentials configured
- **WHEN** either `GOOGLE_CLIENT_ID` or `GOOGLE_CLIENT_SECRET` is absent from the environment
- **AND** a request is made to `/api/v1/auth/google/login` or `/api/v1/auth/google/callback`
- **THEN** the endpoint SHALL return HTTP 503 with a message indicating Google login is not configured

---

### Requirement: Login endpoint returns Google authorization URL
The system SHALL expose `GET /api/v1/auth/google/login`. This endpoint SHALL generate a Google authorization URL including the `openid`, `email`, and `profile` scopes, a `redirect_uri` pointing to the callback endpoint, and a cryptographically random `state` value. The endpoint SHALL store the `state` value in a short-lived `HttpOnly` cookie (`max_age=300`, `SameSite=Lax`, `Secure` in non-local environments) and return a redirect (HTTP 302) to the generated authorization URL.

#### Scenario: User visits login endpoint
- **WHEN** a GET request is made to `/api/v1/auth/google/login`
- **THEN** the response SHALL be an HTTP 302 redirect whose `Location` header points to `accounts.google.com/o/oauth2/auth`
- **AND** the response SHALL set a cookie named `oauth_state` containing the same `state` value embedded in the `Location` URL

#### Scenario: Authorization URL contains required parameters
- **WHEN** the authorization URL is generated
- **THEN** it SHALL include `client_id`, `redirect_uri`, `response_type=code`, `scope` (containing `email` and `profile`), and `state` as query parameters

---

### Requirement: Callback endpoint exchanges code and provisions user
The system SHALL expose `GET /api/v1/auth/google/callback`. This endpoint SHALL:
1. Return HTTP 503 if `GOOGLE_CLIENT_ID` or `GOOGLE_CLIENT_SECRET` is absent (unchanged).
2. If Google redirected back with a non-empty `error` query parameter (e.g., `access_denied`), redirect (HTTP 302) to `{FRONTEND_HOST}/auth/callback?error=access_denied` and delete the `oauth_state` cookie. No token exchange SHALL be attempted.
3. Validate the `state` query parameter against the `oauth_state` cookie value; if the cookie is absent, redirect (HTTP 302) to `{FRONTEND_HOST}/auth/callback?error=missing_state`. No token exchange SHALL be attempted.
4. If `state` does not match the `oauth_state` cookie, redirect (HTTP 302) to `{FRONTEND_HOST}/auth/callback?error=state_mismatch`. Delete the `oauth_state` cookie.
5. Exchange the `code` query parameter for a Google access token by POSTing to Google's token endpoint; on any non-2xx response or transport error, redirect (HTTP 302) to `{FRONTEND_HOST}/auth/callback?error=google_unreachable`.
6. Fetch the authenticated user's `email`, `name`, and `email_verified` fields from Google's userinfo endpoint; on any non-2xx response or transport error, redirect (HTTP 302) to `{FRONTEND_HOST}/auth/callback?error=google_unreachable`.
7. If `email_verified` is not `true`, redirect (HTTP 302) to `{FRONTEND_HOST}/auth/callback?error=unverified_email`. No user SHALL be provisioned.
8. Look up the user by email in the `User` table.
9. If the user does not exist, create a new `User` with `is_active=True`, `is_superuser=False`, `hashed_password=None`, and the Google-provided `full_name`.
10. Issue a native JWT with the standard expiry (`ACCESS_TOKEN_EXPIRE_MINUTES`) for the resolved or newly created user.
11. Delete the `oauth_state` cookie and redirect (HTTP 302) to `{FRONTEND_HOST}/auth/callback?access_token=<jwt>`.

#### Scenario: Valid callback with new user
- **WHEN** a GET request arrives at `/api/v1/auth/google/callback` with a valid `code` and matching `state`
- **AND** no user with the Google email exists in the database
- **THEN** a new `User` SHALL be created with `is_active=True`, `is_superuser=False`, and `hashed_password=NULL`
- **AND** the response SHALL redirect to `FRONTEND_HOST/auth/callback` with a valid `access_token` query parameter

#### Scenario: Valid callback with returning user
- **WHEN** a GET request arrives at `/api/v1/auth/google/callback` with a valid `code` and matching `state`
- **AND** a user with the Google email already exists in the database
- **THEN** no new user SHALL be created
- **AND** the response SHALL redirect to `FRONTEND_HOST/auth/callback` with a valid `access_token` for the existing user

#### Scenario: State mismatch (CSRF attempt)
- **WHEN** the `state` query parameter does not match the `oauth_state` cookie value
- **THEN** the endpoint SHALL respond with HTTP 302 redirecting to `FRONTEND_HOST/auth/callback?error=state_mismatch`
- **AND** no user lookup or creation SHALL occur
- **AND** the `oauth_state` cookie SHALL be deleted

#### Scenario: Missing state cookie
- **WHEN** the `oauth_state` cookie is absent from the request
- **THEN** the endpoint SHALL respond with HTTP 302 redirecting to `FRONTEND_HOST/auth/callback?error=missing_state`
- **AND** no token exchange SHALL be attempted

#### Scenario: Google returns unverified email
- **WHEN** Google's userinfo response contains `email_verified: false`
- **THEN** the endpoint SHALL respond with HTTP 302 redirecting to `FRONTEND_HOST/auth/callback?error=unverified_email`
- **AND** no user SHALL be provisioned

#### Scenario: Token exchange fails
- **WHEN** Google's token endpoint returns a non-2xx response or a transport error occurs
- **THEN** the endpoint SHALL respond with HTTP 302 redirecting to `FRONTEND_HOST/auth/callback?error=google_unreachable`
- **AND** the raw Google error body SHALL NOT appear in the redirect URL

#### Scenario: Userinfo fetch fails
- **WHEN** Google's userinfo endpoint returns a non-2xx response or a transport error occurs
- **THEN** the endpoint SHALL respond with HTTP 302 redirecting to `FRONTEND_HOST/auth/callback?error=google_unreachable`
- **AND** the raw Google error body SHALL NOT appear in the redirect URL

---

### Requirement: User denies Google consent (access_denied short-circuit)
When Google redirects back to the callback with a non-empty `error` query parameter (e.g., `error=access_denied`) instead of `code=…`, the callback SHALL redirect (HTTP 302) to `{FRONTEND_HOST}/auth/callback?error=access_denied` without attempting any token exchange. The `oauth_state` cookie SHALL be deleted.

#### Scenario: User denies consent on Google's consent screen
- **WHEN** a GET request arrives at `/api/v1/auth/google/callback` with `?error=access_denied` (or any non-empty `error` parameter) and no `code`
- **THEN** the endpoint SHALL respond with HTTP 302 redirecting to `FRONTEND_HOST/auth/callback?error=access_denied`
- **AND** no token exchange SHALL be attempted
- **AND** the `oauth_state` cookie SHALL be deleted

---

### Requirement: Error code allowlist enforced
The `error` query parameter in all error redirects SHALL always be one of the following values: `state_mismatch`, `missing_state`, `unverified_email`, `google_unreachable`, `access_denied`. The backend SHALL NOT propagate raw Google error codes, exception messages, or stack traces into the redirect URL.

#### Scenario: Error redirect uses allowlisted code only
- **WHEN** any recoverable failure occurs during the callback flow
- **THEN** the `error` query parameter in the redirect URL SHALL be exactly one value from the allowlist
- **AND** no raw Google API error string or exception detail SHALL appear in the URL

---

### Requirement: Password login rejected for OAuth-only accounts
The `POST /api/v1/login/access-token` endpoint SHALL reject authentication attempts for users whose `hashed_password` is `NULL`, returning HTTP 400 with a message indicating the account was created via Google and requires Google login.

#### Scenario: OAuth user attempts password login
- **WHEN** a POST to `/api/v1/login/access-token` is made with the email of a Google-provisioned user
- **THEN** the response SHALL be HTTP 400
- **AND** the response body SHALL indicate that the account uses Google login

---

### Requirement: User model supports null password
The `User` database model SHALL allow `hashed_password` to be `NULL`. An Alembic migration SHALL make the column nullable. Existing users with hashed passwords SHALL be unaffected.

#### Scenario: OAuth user record persisted correctly
- **WHEN** a new Google user is provisioned through the callback endpoint
- **THEN** the `User` row in the database SHALL have `hashed_password = NULL`
- **AND** all other fields (`id`, `email`, `full_name`, `is_active`, `is_superuser`) SHALL be set correctly

---

### Requirement: Test coverage for Google OAuth endpoints
The test suite SHALL include unit tests for `GET /api/v1/auth/google/login` and `GET /api/v1/auth/google/callback`. All HTTP calls to Google APIs (token endpoint, userinfo endpoint) SHALL be mocked so tests run without network access. Tests SHALL cover: successful new-user flow, successful returning-user flow, state mismatch rejection, missing state cookie rejection, and unverified-email rejection.

#### Scenario: Callback test runs without network access
- **WHEN** the test suite executes the callback endpoint tests
- **THEN** no real HTTP requests to `accounts.google.com` or `googleapis.com` SHALL be made
- **AND** all tests SHALL pass in an isolated environment
