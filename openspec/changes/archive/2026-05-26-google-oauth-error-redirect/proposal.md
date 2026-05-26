## Why

The backend Google OAuth callback currently returns raw HTTP 400 JSON errors on failure paths (state mismatch, missing cookie, unverified email, token-exchange failure), leaving users on a FastAPI error page after returning from Google. The frontend (Ticket 004) already expects `${FRONTEND_HOST}/auth/callback?error=<code>` redirects, so the backend must honor that contract to complete the UX loop.

## What Changes

- State mismatch: returns HTTP 400 → redirects to `/auth/callback?error=state_mismatch`
- Missing `oauth_state` cookie: returns HTTP 400 → redirects to `/auth/callback?error=missing_state`
- Unverified email: returns HTTP 400 → redirects to `/auth/callback?error=unverified_email`
- Token exchange / userinfo failure: currently unhandled exception → redirects to `/auth/callback?error=google_unreachable`
- **New**: User denies Google consent (`?error=access_denied` from Google) → redirects to `/auth/callback?error=access_denied` (short-circuit, no token exchange attempted)
- HTTP 503 on missing credentials: **unchanged** (out of scope — deployment misconfiguration signal)
- Error code allowlist: a `Literal[...]` type enforces only the 5 defined codes reach the redirect URL
- Existing tests updated to assert HTTP 302 + correct `Location`; new test added for access_denied short-circuit

## Capabilities

### New Capabilities
- (none)

### Modified Capabilities
- `google-oauth`: Three existing failure scenarios change from HTTP 400 responses to HTTP 302 redirects (state mismatch, missing cookie, unverified email); two requirements added (access_denied short-circuit, token-exchange failure redirect)

## Impact

- `backend/app/api/routes/google_auth.py` — all failure paths in the callback refactored to redirect
- `backend/tests/api/routes/test_google_auth.py` — existing 400 assertions updated to 302; new test added
- `openspec/specs/google-oauth/spec.md` — three scenarios modified, two requirements added
