## Context

The backend Google OAuth flow (capability `google-oauth`) is in place: `GET /api/v1/auth/google/login` issues a 302 to Google, and the callback at `/api/v1/auth/google/callback` redirects to `${FRONTEND_HOST}/auth/callback?access_token=<jwt>` on success. The React/Vite frontend already manages auth state in `frontend/src/hooks/useAuth.ts` using TanStack Query (`currentUser` query) and `localStorage` (`access_token` key). Email/password login is the only existing entry point.

Constraints:
- Routing is **file-based** via TanStack Router. New routes are added by creating files under `frontend/src/routes/`; `routeTree.gen.ts` is auto-regenerated and committed (see recent commit `1575456`).
- UI components come from Shadcn/UI (`frontend/src/components/ui/*`). The login/signup screens already use `LoadingButton`, `Form`, etc.
- Tests live in `frontend/tests/` and run via Playwright against `http://localhost:5173`.
- The backend lives at `VITE_API_URL` (typically `http://localhost:8000`); the frontend cannot use a relative URL for the Google login redirect.

## Goals / Non-Goals

**Goals:**
- Users can click "Continue with Google" on `/login` or `/signup` and complete a full sign-in/sign-up cycle, ending up authenticated on `/`.
- Token capture happens **before** any UI renders for `/auth/callback`, so the JWT never appears in the visible URL bar and is removed from browser history.
- Error paths (denied consent, backend 503, mismatched state) end on `/login` with a user-friendly toast — never a blank page.
- Reuse the existing `useAuth` plumbing (`localStorage` + `currentUser` query invalidation) rather than introducing a parallel auth state.

**Non-Goals:**
- No account-linking UI for users who already have a password account but try Google with the same email — the backend simply logs them in to the existing account, which is the desired behavior; no extra confirmation screen.
- No "Sign in with Google" One Tap / GIS JavaScript SDK integration. The flow is server-driven (backend redirects to Google directly), which keeps secrets out of the client.
- No refresh-token handling on the frontend — the issued JWT follows the same expiry rules as password login; users re-authenticate via the same Google button when it expires.
- No logout-from-Google behavior. Local logout clears `access_token` only.

## Decisions

### D1: Full-page navigation to start the OAuth flow (not `fetch`)

Use `window.location.assign(`${import.meta.env.VITE_API_URL}/api/v1/auth/google/login`)` when the button is clicked.

**Why:** The backend responds with a 302 to `accounts.google.com`. A `fetch` call would either follow the redirect opaquely (CORS-blocked) or be intercepted by the browser. A full-page navigation lets the browser handle the redirect chain cleanly and ensures the `oauth_state` cookie set by the backend is stored on the same origin as the eventual callback.

**Alternative considered:** Open the flow in a popup window and `postMessage` the token back. Rejected — heavier, popup-blocker risk, and the backend already implements the redirect-back contract.

### D2: Capture the token in `beforeLoad`, not in the component

The `/auth/callback` route uses TanStack Router's `beforeLoad` (or `loader`) to read `Route.useSearch()` synchronously, persist the token to `localStorage`, invalidate the `currentUser` query, and `throw redirect({ to: "/" })` — all before the component renders.

**Why:** Acceptance Criterion AC5 ("Ensure the UI cleans up any URL parameters containing the token for security reasons") and the implementation note about preventing UI flicker. Doing the work in `beforeLoad` means no component ever mounts with the token in its URL.

**Alternative considered:** Use a `useEffect` inside a `CallbackPage` component. Rejected — the token would be visible in the URL bar for at least one render frame, and would persist in `history` until `navigate` ran.

### D3: New `loginWithGoogleToken` helper on `useAuth`

Add a small helper to `useAuth.ts`:

```ts
const loginWithGoogleToken = (token: string) => {
  localStorage.setItem("access_token", token)
  queryClient.invalidateQueries({ queryKey: ["currentUser"] })
}
```

The `/auth/callback` `beforeLoad` cannot call hooks, so it instead calls the underlying `localStorage` + `queryClient.invalidateQueries` directly — but those two lines are the same shape as the helper. Export the helper anyway so any future component (e.g., a settings page that re-links Google) can reuse it.

**Why:** Keeps token persistence centralized. The existing `login` function (password flow) sets `access_token` in the same key; this just adds the OAuth equivalent.

### D4: Gate the Google button on `VITE_GOOGLE_LOGIN_ENABLED`

Read `import.meta.env.VITE_GOOGLE_LOGIN_ENABLED === "true"` at module level. When `false` (or unset), the `GoogleLoginButton` component renders `null`.

**Why:** The backend returns HTTP 503 when `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` are missing. A button that always 503s is a poor UX. A build-time flag is acceptable because the deployment that builds the frontend also knows whether the backend has Google configured.

**Alternative considered:** Probe the backend at app start (`GET /api/v1/auth/google/login` with a HEAD request) and hide the button on 503. Rejected — adds a network round-trip on every page load, and the cookie set by the probe could interfere with a later real flow.

### D5: Error surface via `?error=` query param + toast

When the backend cannot complete the flow (e.g., user denied consent, state mismatch), it currently returns HTTP 400 from the callback endpoint. For UX, the backend will need a follow-up that, on failure, redirects to `${FRONTEND_HOST}/auth/callback?error=<code>` rather than returning 400 to the browser. **This is out of scope for ticket 004 itself** — the frontend will handle `?error=` if present (the spec's contract), but the existing backend behavior is unchanged. We document the gap so the next iteration on capability `google-oauth` can add the redirect.

**Why:** Without this contract, a denied consent leaves the user staring at a JSON error page from FastAPI. The frontend route will be ready when the backend catches up.

## Risks / Trade-offs

- **[Risk] Open redirect via crafted `access_token` query param**: Anyone can navigate to `/auth/callback?access_token=<garbage>` and trigger a `localStorage.setItem`. → **Mitigation:** The token is only validated when `UsersService.readUserMe` runs after `invalidateQueries`. A garbage token causes a 401, which `main.tsx`'s `handleApiError` already catches and redirects to `/login` while clearing the token. No new attack surface beyond existing behavior.
- **[Risk] Backend redirects to `/auth/callback` but the user has the tab open for `/auth/callback` from a previous flow**: TanStack Router will treat the new URL as a navigation; `beforeLoad` re-runs with the new search params. ✔ Safe by design.
- **[Trade-off] Build-time flag instead of runtime detection**: A single frontend build cannot serve both Google-enabled and Google-disabled backends. Acceptable because deployments are 1:1 with backend config in this project.
- **[Trade-off] No refresh of the `currentUser` query is awaited before redirecting**: After `invalidateQueries`, we `redirect({ to: "/" })` immediately. The `/` route will refetch on mount. If the JWT is invalid, the user briefly sees `/` before being bounced to `/login` by `handleApiError`. Acceptable — same behavior as a stale token on page reload.

## Open Questions

- Should the Google button appear on `/signup` even though, from the backend's perspective, there is no distinction between "sign up" and "log in" via Google? Recommendation: yes, label it identically on both screens ("Continue with Google") since the UX expectation is parity with email/password.
- Naming: route file `auth.callback.tsx` (TanStack Router flat naming → `/auth/callback`) vs nested `auth/callback.tsx` (folder). Pick whichever matches the existing convention; current routes are flat at the top level (`login.tsx`, `signup.tsx`) — propose `auth.callback.tsx` for consistency. Resolved during implementation.
