# Ticket 005: Google OAuth Error Redirect

## 1. Objective

Change the backend Google OAuth callback (`GET /api/v1/auth/google/callback`) so that recoverable failures redirect the user back to the frontend with a structured `error` query parameter, instead of returning an HTTP 4xx JSON response. This completes the contract that the frontend already assumes (see Ticket 004) and gives users a coherent UX when something goes wrong.

## 2. Context

Ticket 003 implemented the Google OAuth flow on the backend. On the happy path, the callback redirects to `${FRONTEND_HOST}/auth/callback?access_token=<jwt>`. On the failure paths (state mismatch, missing `oauth_state` cookie, unverified email, token-exchange failure, userinfo failure), the callback currently raises an `HTTPException` with status 400. From the browser's perspective that means the user lands on a raw FastAPI JSON error page after returning from Google — a broken-looking experience.

Ticket 004 (frontend Google login) already expects the backend to redirect to `${FRONTEND_HOST}/auth/callback?error=<code>` so that the frontend route can clean up the URL and surface a friendly toast on `/login`. This ticket closes the loop by making the backend honor that contract.

The HTTP 503 response when Google credentials are not configured (login endpoint or callback called without `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET`) is explicitly out of scope — that is a deployment-misconfiguration signal, not a recoverable user-facing failure, and the current 503 behavior should stay.

## 3. Acceptance Criteria (AC)

- **AC1:** State mismatch redirects. When the `state` query parameter does not match the `oauth_state` cookie, the callback SHALL redirect (HTTP 302) to `${FRONTEND_HOST}/auth/callback?error=state_mismatch` instead of returning HTTP 400. The `oauth_state` cookie SHALL still be deleted as part of the response.
- **AC2:** Missing state cookie redirects. When the `oauth_state` cookie is absent from the request, the callback SHALL redirect (HTTP 302) to `${FRONTEND_HOST}/auth/callback?error=missing_state` instead of returning HTTP 400. No token exchange SHALL be attempted.
- **AC3:** Unverified email redirects. When Google's userinfo response contains `email_verified: false`, the callback SHALL redirect (HTTP 302) to `${FRONTEND_HOST}/auth/callback?error=unverified_email` instead of returning HTTP 400. No user SHALL be provisioned.
- **AC4:** Token exchange / userinfo failures redirect. When the POST to Google's token endpoint or the GET to the userinfo endpoint returns a non-2xx response (or raises a transport error), the callback SHALL redirect (HTTP 302) to `${FRONTEND_HOST}/auth/callback?error=google_unreachable`. The original Google error body MAY be logged server-side but SHALL NOT be exposed to the client.
- **AC5:** User denies consent. When Google itself redirects back to the callback with `?error=access_denied` (or any non-empty `error` query parameter from Google) instead of `?code=…`, the callback SHALL redirect (HTTP 302) to `${FRONTEND_HOST}/auth/callback?error=access_denied`. No token exchange SHALL be attempted. The `oauth_state` cookie SHALL be deleted.
- **AC6:** 503 behavior preserved for missing credentials. The existing HTTP 503 response when `GOOGLE_CLIENT_ID` or `GOOGLE_CLIENT_SECRET` is missing SHALL remain unchanged on both `/api/v1/auth/google/login` and `/api/v1/auth/google/callback`. (Deployment misconfiguration, not user-facing.)
- **AC7:** Error code allowlist. The `error` query parameter SHALL always be one of a small, documented allowlist: `state_mismatch`, `missing_state`, `unverified_email`, `google_unreachable`, `access_denied`. The backend SHALL NOT propagate raw Google error codes or stack-trace messages into the redirect URL.
- **AC8:** Test coverage. Existing tests in `backend/tests/api/routes/test_google_auth.py` that previously asserted HTTP 400 SHALL be updated to assert HTTP 302 with the expected `Location` (frontend host + `/auth/callback?error=<code>`). A new test SHALL cover the `?error=access_denied` short-circuit (AC5).

## 4. Implementation Notes

- The `RedirectResponse` for error cases should mirror the cookie handling of the success path (delete `oauth_state` so a stale cookie does not poison a retry).
- Consider centralizing the redirect-with-error in a small helper inside `backend/app/api/routes/google_auth.py` (e.g. `_redirect_to_frontend_error(code: str) -> RedirectResponse`) to keep the call sites uniform and to make AC7 (allowlist) trivially enforceable via a `Literal[...]` type.
- The frontend already shows a single generic toast ("Google login failed. Please try again or use email and password.") for any `error` value — the codes are for logging and future per-code messaging, not currently shown to the user.
- This change modifies the existing `google-oauth` OpenSpec capability rather than adding a new one. Three requirements need MODIFIED deltas (state mismatch, missing state cookie, unverified email); two requirements are ADDED (access_denied short-circuit, token-exchange failure redirect). The 503-on-missing-credentials requirement is unchanged.
- Suggested OpenSpec change name: `google-oauth-error-redirect`.
