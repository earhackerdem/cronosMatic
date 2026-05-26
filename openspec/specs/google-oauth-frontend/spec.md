# Spec: Google OAuth Frontend

## Purpose

Defines requirements for the React/Vite frontend integration of Google OAuth 2.0 login. Covers the UI entry points on the login and signup screens, the `/auth/callback` route that captures the backend-issued JWT, the auth-state integration that consumes the token through the existing `useAuth` hook, and the Playwright test coverage that exercises the flow in isolation from real Google services. The backend half of this flow lives in capability `google-oauth`.

## Requirements

### Requirement: Google login entry point on auth screens
The frontend SHALL render a "Continue with Google" button on both `/login` and `/signup` whenever the build-time flag `VITE_GOOGLE_LOGIN_ENABLED` is the string `"true"`. The button SHALL be visually distinct from the primary email/password submit control and SHALL use the existing Shadcn/UI component styling so it integrates with the surrounding form. When the flag is unset or has any other value, the button SHALL NOT be rendered (it SHALL produce no DOM output and no surrounding container).

#### Scenario: Flag enabled — button visible on login
- **WHEN** `VITE_GOOGLE_LOGIN_ENABLED=true` at build time
- **AND** the user visits `/login`
- **THEN** a button labeled "Continue with Google" SHALL be present in the auth form

#### Scenario: Flag enabled — button visible on signup
- **WHEN** `VITE_GOOGLE_LOGIN_ENABLED=true` at build time
- **AND** the user visits `/signup`
- **THEN** a button labeled "Continue with Google" SHALL be present in the auth form

#### Scenario: Flag disabled — button hidden
- **WHEN** `VITE_GOOGLE_LOGIN_ENABLED` is unset, empty, or any value other than the string `"true"`
- **AND** the user visits `/login` or `/signup`
- **THEN** no element matching the Google login button (by accessible name or test id) SHALL be present

---

### Requirement: Clicking the Google button initiates the backend OAuth flow
Clicking the "Continue with Google" button SHALL trigger a full-page navigation to `${VITE_API_URL}/api/v1/auth/google/login`. The frontend SHALL NOT use `fetch` or `XMLHttpRequest` for this navigation — it MUST be a real browser navigation so that the backend's 302 redirect chain to Google and the resulting `oauth_state` cookie are processed by the browser.

#### Scenario: Button click triggers full-page navigation
- **WHEN** the user clicks "Continue with Google"
- **THEN** the browser SHALL navigate (via `window.location` assignment or equivalent) to `${VITE_API_URL}/api/v1/auth/google/login`
- **AND** no `fetch` or `XMLHttpRequest` SHALL be issued by the click handler

---

### Requirement: `/auth/callback` route captures token before render
The frontend SHALL expose a route at `/auth/callback`. When this route receives an `access_token` search parameter, it SHALL persist the token to `localStorage` under the key `access_token`, invalidate the TanStack Query cache entry keyed `["currentUser"]`, and redirect the user to `/` — all within the route's `beforeLoad` (or equivalent pre-render hook) so that no component renders with the token visible in the URL.

#### Scenario: Callback with valid `access_token` redirects to dashboard
- **WHEN** the user navigates to `/auth/callback?access_token=<jwt>`
- **THEN** `localStorage.getItem("access_token")` SHALL equal `<jwt>` after the navigation settles
- **AND** the user SHALL end up at `/`
- **AND** the URL bar SHALL NOT contain the `access_token` query parameter at any rendered frame

#### Scenario: Callback without `access_token` or `error` redirects to login
- **WHEN** the user navigates to `/auth/callback` with neither `access_token` nor `error` present
- **THEN** the user SHALL be redirected to `/login`
- **AND** `localStorage.getItem("access_token")` SHALL be unchanged

---

### Requirement: `/auth/callback` handles error parameter with toast
When the `/auth/callback` route receives an `error` search parameter, it SHALL redirect the user to `/login` and surface a user-friendly toast (via the existing `useCustomToast` mechanism) explaining that Google login failed. The toast message SHALL NOT contain raw error codes — it SHALL be a human-readable string such as "Google login failed. Please try again or use email and password." The `error` parameter SHALL NOT remain in the URL after redirection.

#### Scenario: Callback with `error` param shows toast and redirects
- **WHEN** the user navigates to `/auth/callback?error=access_denied`
- **THEN** the user SHALL be redirected to `/login`
- **AND** a toast SHALL be displayed indicating Google login failed
- **AND** `localStorage.getItem("access_token")` SHALL be unchanged

---

### Requirement: Auth state integration via existing hook
The frontend SHALL extend `useAuth` with a `loginWithGoogleToken(token: string)` helper that persists the token to `localStorage` (key `access_token`) and invalidates the `["currentUser"]` query. The `/auth/callback` pre-render logic MAY perform these two operations directly (since it runs outside React) but SHALL NOT duplicate the persistence key or the query key — both MUST match exactly the values used by `useAuth`'s password-login flow.

#### Scenario: Helper sets token under the same key as password login
- **WHEN** `loginWithGoogleToken("abc123")` is invoked
- **THEN** `localStorage.getItem("access_token")` SHALL return `"abc123"`
- **AND** the `["currentUser"]` query SHALL be invalidated

#### Scenario: Callback pre-render uses the same storage key
- **WHEN** the `/auth/callback` route persists the token from its search params
- **THEN** the storage key SHALL be `access_token` (matching `useAuth`'s password-login path)

---

### Requirement: Test coverage for Google login UI
The Playwright test suite SHALL include scenarios that exercise the frontend Google login UI without depending on real Google services. Tests SHALL cover: button visibility under the enabled flag, button click navigating to the backend login endpoint, successful callback navigation, and error callback navigation. The actual OAuth flow with Google MAY be stubbed by navigating directly to `/auth/callback?access_token=<jwt>` or `/auth/callback?error=<code>`.

#### Scenario: Test suite runs without real Google calls
- **WHEN** the Playwright spec for Google login runs
- **THEN** no test SHALL navigate to `accounts.google.com`
- **AND** all assertions SHALL pass against the local frontend in isolation
