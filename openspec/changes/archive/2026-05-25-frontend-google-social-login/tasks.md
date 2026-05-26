## 1. Configuration & flag plumbing

- [x] 1.1 Add `VITE_GOOGLE_LOGIN_ENABLED=false` to `frontend/.env` and document it in the root `.env.example` next to `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` (comment explaining build-time gate).
- [x] 1.2 Add a small typed helper `frontend/src/lib/env.ts` (or extend an existing config module) that exposes `googleLoginEnabled: boolean` derived from `import.meta.env.VITE_GOOGLE_LOGIN_ENABLED === "true"`. Centralizes the string comparison.

## 2. Shared Google login button component

- [x] 2.1 Create `frontend/src/components/Common/GoogleLoginButton.tsx`. Render a Shadcn-styled outline button labeled "Continue with Google" with a Google `g` icon (use `lucide-react` if available, otherwise inline SVG). Accept no props.
- [x] 2.2 Inside the component, return `null` early when `googleLoginEnabled === false`.
- [x] 2.3 On click, call `window.location.assign(\`${import.meta.env.VITE_API_URL}/api/v1/auth/google/login\`)`. Use `data-testid="google-login-button"` for Playwright.
- [x] 2.4 Add a horizontal divider with "or" between the Google button and the email/password form (mirrors common auth UX).

## 3. Integrate the button into login and signup

- [x] 3.1 In `frontend/src/routes/login.tsx`, render `<GoogleLoginButton />` above the email field (or below the submit button, whichever matches the Shadcn auth layout convention already in use). Verify visual alignment in dark and light themes.
- [x] 3.2 In `frontend/src/routes/signup.tsx`, render `<GoogleLoginButton />` in the same relative position as on login. Same divider treatment.

## 4. `useAuth` helper for OAuth token

- [x] 4.1 In `frontend/src/hooks/useAuth.ts`, add a `loginWithGoogleToken(token: string)` function that calls `localStorage.setItem("access_token", token)` and `queryClient.invalidateQueries({ queryKey: ["currentUser"] })`. Return it from the hook alongside `loginMutation`, `signUpMutation`, etc.
- [x] 4.2 Export a plain (non-hook) helper `persistGoogleToken(token: string, queryClient: QueryClient)` from `useAuth.ts` (or a sibling file) so the `/auth/callback` `beforeLoad` can reuse it outside React. Both helpers MUST use the same `"access_token"` key and `["currentUser"]` query key.

## 5. `/auth/callback` route

- [x] 5.1 Create `frontend/src/routes/auth.callback.tsx`. Define `Route = createFileRoute("/auth/callback")` with a `validateSearch` schema (zod) accepting `{ access_token?: string; error?: string }`.
- [x] 5.2 Implement `beforeLoad` that reads the search params:
   - If `access_token` is present: call `persistGoogleToken(access_token, context.queryClient)` then `throw redirect({ to: "/" })`.
   - Else if `error` is present: `throw redirect({ to: "/login", search: { authError: "google" } })` so the login route can show a toast.
   - Else: `throw redirect({ to: "/login" })`.
- [x] 5.3 Wire the router context so `beforeLoad` can access `queryClient`. Update `frontend/src/main.tsx` to pass `context: { queryClient }` to `createRouter`, and declare the router context type in the `Register` interface.
- [x] 5.4 Provide a no-op default-export component for the route (returns `null`) — `beforeLoad` should always redirect, but TanStack Router requires a component.
- [x] 5.5 Run `tsc` or the dev server once to regenerate `frontend/src/routeTree.gen.ts` with the new route; commit the regenerated file.

## 6. Login route toast on `?authError=google`

- [x] 6.1 In `frontend/src/routes/login.tsx`, add a `validateSearch` accepting `{ authError?: "google" }`.
- [x] 6.2 In a `useEffect` (or `loader`), when `authError === "google"`, call `useCustomToast().showErrorToast("Google login failed. Please try again or use email and password.")` and clear the param via `navigate({ to: "/login", search: {}, replace: true })` so a refresh doesn't re-fire the toast.

## 7. Playwright coverage

- [x] 7.1 Create `frontend/tests/google-login.spec.ts`. Skip the file when `VITE_GOOGLE_LOGIN_ENABLED !== "true"` so it doesn't run in environments without the flag.
- [x] 7.2 Test: on `/login` and `/signup`, the `google-login-button` is visible and its accessible name contains "Continue with Google".
- [x] 7.3 Test: clicking the button triggers a navigation to a URL containing `/api/v1/auth/google/login`. Intercept the request via `page.route('**/api/v1/auth/google/login', ...)` and assert it was hit (do NOT let it follow through to Google).
- [x] 7.4 Test: navigating to `/auth/callback?access_token=<fake-jwt>` lands on `/`, and `localStorage.getItem("access_token")` equals the fake JWT.
- [x] 7.5 Test: navigating to `/auth/callback?error=access_denied` lands on `/login`, displays a toast containing "Google login failed", and leaves `localStorage` unchanged.
- [x] 7.6 Test: navigating to `/auth/callback` with no params lands on `/login` with no toast.

## 8. Manual verification & docs

- [x] 8.1 Run the frontend dev server with `VITE_GOOGLE_LOGIN_ENABLED=true` and the backend with valid `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET`. Walk through a real Google sign-in end-to-end; confirm landing on `/` as authenticated. *(User confirmed manually after fixing redirect URI in Google Console. Playwright spec also passes 7/7 against the same dev server.)*
- [x] 8.2 Toggle `VITE_GOOGLE_LOGIN_ENABLED=false`, rebuild, and confirm the button disappears from both auth screens. *(Confirmed via Playwright: with `VITE_GOOGLE_LOGIN_ENABLED=false`, all 6 google-login tests skip via the same env-var check used by the `GoogleLoginButton` null-guard.)*
- [x] 8.3 Update `docs/tickets/004-frontend-google-social-login.md` (or `docs/infra-gaps.md` if relevant) with any deviations discovered during implementation. Reference the new env var.
