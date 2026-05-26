## Context

The backend callback at `GET /api/v1/auth/google/callback` raises `HTTPException` (HTTP 400) on all recoverable failure paths. The frontend (Ticket 004) was built to expect `${FRONTEND_HOST}/auth/callback?error=<code>` redirects and already surfaces a toast on `/login` for any non-empty `error` value. The gap between what the backend emits and what the frontend expects means users land on a raw FastAPI JSON error page after returning from Google.

The existing success path already redirects to `${FRONTEND_HOST}/auth/callback?access_token=<jwt>` and deletes the `oauth_state` cookie. Error paths need the same cookie cleanup to prevent a stale cookie from poisoning retries.

HTTP 503 for missing credentials is explicitly out of scope — it is a deployment-misconfiguration signal, not a user-facing recoverable error, and its current behavior must not change.

## Goals / Non-Goals

**Goals:**
- All recoverable failure paths in the callback redirect to `${FRONTEND_HOST}/auth/callback?error=<code>` (HTTP 302)
- Error codes come from a small, documented allowlist (never raw Google error strings or stack traces)
- `oauth_state` cookie is deleted in all error redirects
- Existing tests updated; new test added for the access_denied short-circuit

**Non-Goals:**
- Changing HTTP 503 behavior on missing credentials
- Per-error-code UI messaging (frontend currently shows a single generic toast for all codes)
- Changing the login endpoint (`/api/v1/auth/google/login`)

## Decisions

### D1: Centralize error redirects in a `_redirect_error` helper

All five error codes flow through a single helper:
```python
ErrorCode = Literal["state_mismatch", "missing_state", "unverified_email", "google_unreachable", "access_denied"]

def _redirect_error(code: ErrorCode) -> RedirectResponse:
    response = RedirectResponse(url=f"{settings.FRONTEND_HOST}/auth/callback?error={code}", status_code=302)
    response.delete_cookie(key=_OAUTH_STATE_COOKIE)
    return response
```

**Why**: The `Literal[...]` type makes AC7 (allowlist) trivially enforceable — mypy/pyright reject any code not in the union. Cookie deletion is guaranteed for all error paths in one place. **Alternative considered**: inline `RedirectResponse` at each call site — rejected because it scatters cookie deletion and makes the allowlist enforcement implicit.

### D2: Handle Google's `?error=` query parameter as the first check in the callback

Google can redirect back with `?error=access_denied` (user denied consent) or other OAuth error codes, without providing `?code=`. This check must happen before state validation to avoid a misleading `missing_state` or `state_mismatch` code when the real cause is user denial.

Check order in the callback:
1. Credentials present? (503 guard — unchanged)
2. Google returned `?error=`? → `_redirect_error("access_denied")` (new early exit)
3. `oauth_state` cookie present? → `_redirect_error("missing_state")`
4. `state` matches cookie? → `_redirect_error("state_mismatch")`
5. Token exchange succeeds? → `_redirect_error("google_unreachable")`
6. Userinfo fetch succeeds? → `_redirect_error("google_unreachable")`
7. Email verified? → `_redirect_error("unverified_email")`
8. Provision/lookup user → redirect with JWT (success path, unchanged)

**Why**: This order matches the semantics. Google errors are external signals that arrive before we even have a `code` to exchange, so they should short-circuit before any local state checks.

### D3: Log raw Google error body server-side, never in the redirect URL

When token exchange or userinfo fetch returns non-2xx, log the status and response body at WARNING level before redirecting with `google_unreachable`. The client only ever sees the code.

**Why**: AC4 explicitly allows server-side logging. Raw Google error bodies (e.g., `"invalid_grant"`) would expose internal API detail and are not actionable by the user.

## Risks / Trade-offs

- [Risk] The `google_callback` function signature gains an `error` parameter (`str | None = None`) — this is a new FastAPI query parameter with a default, so it is fully backwards-compatible. → No mitigation needed beyond the default.
- [Risk] Tests that currently assert `status_code == 400` will fail until updated. → All affected tests are in `test_google_auth.py` and are directly in scope for AC8.
- [Trade-off] A single generic error code `google_unreachable` covers both token-exchange failures and userinfo failures. Fine for now because the frontend shows one toast regardless — add per-code distinction only if future per-code messaging is needed.
