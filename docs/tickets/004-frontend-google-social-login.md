# Ticket 004: Frontend Google Social Login Integration

## 1. Objective

Implement the UI and state management logic in the React/Vite frontend to consume the Google OAuth 2.0 endpoints created in the backend, enabling a seamless login and registration experience.

## 2. Context

The backend has been updated (Ticket 003) to handle the Google OAuth flow and issue a native JWT upon successful authentication. The frontend now needs a "Login with Google" interface. It must trigger the redirection to the backend's Google login endpoint and handle the subsequent return flow. The frontend must capture the issued JWT, update the application's authentication state, and redirect the user to the main dashboard.

## 3. Acceptance Criteria (AC)

- **AC1:** UI Integration. Add a distinct "Login with Google" button on both the Login and Registration views. Ensure the design aligns with the existing UI components (e.g., Chakra UI or the styling framework provided by the Tiangolo template).
- **AC2:** Redirection Logic. Clicking the "Login with Google" button must redirect the user to the backend's authorization endpoint (e.g., `GET /api/v1/auth/google/login`), which will then forward them to the Google consent screen.
- **AC3:** Callback Routing & Token Capture. Implement a frontend route or logic to handle the return from the backend after a successful Google login. 
  - *Note:* Depending on the backend implementation, the backend callback might redirect to a frontend URL with the token in the URL parameters (e.g., `http://localhost:5173/login?access_token=<JWT>`), or set an HTTP-only cookie. The frontend must intercept this token.
- **AC4:** State Management. Upon capturing the JWT, securely store it using the existing frontend authentication mechanism (typically `localStorage` in the Tiangolo template) and update the global auth state/context to reflect that the user is logged in.
- **AC5:** Post-Login Navigation. After successfully saving the token and updating the state, automatically redirect the user to the application's Dashboard. Ensure the UI cleans up any URL parameters containing the token for security reasons.

## 4. Implementation Notes

- Review the `src/hooks/useAuth.ts` or equivalent authentication context in the Tiangolo frontend structure to reuse the existing `login` state updater functions rather than reinventing the wheel.
- If the backend passes the token via a URL query parameter during the redirect, ensure `react-router-dom` (or the routing library in use) catches it before rendering the view to prevent UI flickering.
- Add robust error handling: if the authentication fails or the user denies consent, display a clear, user-friendly error toast or message on the login screen.

## 5. Implementation Notes (post-implementation)

Tracked as OpenSpec change `frontend-google-social-login` (capability `google-oauth-frontend`). Notable additions over the original ACs:

- **New env var `VITE_GOOGLE_LOGIN_ENABLED`** (build-time, frontend): gates rendering of the "Continue with Google" button. Defaults to `false`; set to `"true"` only when the backend has `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` configured (otherwise the button would 503).
- **Router context now carries `queryClient`**: `__root.tsx` switched from `createRootRoute` to `createRootRouteWithContext<{ queryClient }>()`, and `main.tsx` passes it via `createRouter({ ..., context: { queryClient } })`. This lets the `/auth/callback` route's `beforeLoad` invalidate the `["currentUser"]` query outside React.
- **Error contract awaits backend follow-up**: the frontend handles `/auth/callback?error=<code>` by toasting and bouncing to `/login`, but the backend currently returns HTTP 400 on OAuth failures instead of redirecting. Tracked as **Ticket 005 (`google-oauth-error-redirect`)**.
