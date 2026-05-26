## 1. Backend: error redirect helper

- [x] 1.1 Add `ErrorCode = Literal["state_mismatch", "missing_state", "unverified_email", "google_unreachable", "access_denied"]` type alias in `backend/app/api/routes/google_auth.py`
- [x] 1.2 Implement `_redirect_error(code: ErrorCode) -> RedirectResponse` helper that redirects to `{FRONTEND_HOST}/auth/callback?error={code}` (HTTP 302) and deletes the `oauth_state` cookie

## 2. Backend: refactor callback failure paths

- [x] 2.1 Add `error: str | None = None` query parameter to `google_callback` function signature
- [x] 2.2 Add early-exit check: if `error` is non-empty, return `_redirect_error("access_denied")` (before any state checks)
- [x] 2.3 Replace `raise HTTPException(400, "Missing OAuth state cookie.")` with `return _redirect_error("missing_state")`
- [x] 2.4 Replace `raise HTTPException(400, "Invalid OAuth state...")` with `return _redirect_error("state_mismatch")`
- [x] 2.5 Replace `raise HTTPException(400, "Failed to exchange authorization code.")` and the missing-access-token guard with `return _redirect_error("google_unreachable")`; log the Google response body at WARNING level
- [x] 2.6 Replace `raise HTTPException(400, "Failed to fetch user info from Google.")` with `return _redirect_error("google_unreachable")`; log the Google response body at WARNING level
- [x] 2.7 Replace `raise HTTPException(400, "Google account email is not verified.")` with `return _redirect_error("unverified_email")`

## 3. Tests: update existing assertions

- [x] 3.1 Update `test_google_callback_state_mismatch`: assert `status_code == 302` and `Location` header contains `error=state_mismatch`; assert `FRONTEND_HOST` is in the `Location`
- [x] 3.2 Update `test_google_callback_missing_state_cookie`: assert `status_code == 302` and `Location` header contains `error=missing_state`
- [x] 3.3 Update `test_google_callback_unverified_email`: assert `status_code == 302` and `Location` header contains `error=unverified_email`
- [x] 3.4 Update `test_google_callback_token_exchange_failure`: assert `status_code == 302` and `Location` header contains `error=google_unreachable`

## 4. Tests: new test for access_denied short-circuit

- [x] 4.1 Add `test_google_callback_access_denied`: call `/api/v1/auth/google/callback?error=access_denied` (no `code`), assert HTTP 302 with `Location` containing `error=access_denied`; confirm no `code` exchange is attempted (no `httpx.Client` mock needed)

## 5. Verify

- [x] 5.1 Run `pytest backend/tests/api/routes/test_google_auth.py -v` and confirm all tests pass
- [x] 5.2 Confirm no test asserts HTTP 400 for the modified failure paths
