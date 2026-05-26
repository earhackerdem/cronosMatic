# Ticket 003: Google Social Login (OAuth 2.0) Integration

## 1. Objective
Implement Google OAuth 2.0 authentication in the FastAPI backend to allow users to register and log in seamlessly, reducing onboarding friction.

## 2. Context
Currently, the Tiangolo template relies exclusively on a standard email and password flow generating a local JWT. To increase conversion rates, the platform must support Social Login. The system needs to handle the OAuth 2.0 flow, retrieve the user's email and basic profile from Google, and seamlessly integrate them into the existing `User` database model, ultimately returning the standard native JWT used by the application.

## 3. Acceptance Criteria (AC)
- [ ] **AC1:** Environment variable configuration. Update `.env.example` and the `pydantic-settings` configuration class to include `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`.
- [ ] **AC2:** Implementation of the login endpoint (e.g., `GET /api/v1/auth/google/login`). This endpoint should generate the Google authorization URL and redirect the user (or return the URL for the frontend to handle the redirection).
- [ ] **AC3:** Implementation of the callback endpoint (e.g., `GET /api/v1/auth/google/callback`). This endpoint must securely exchange the authorization code for an access token and fetch the user's profile data (email, name) from the Google API.
- [ ] **AC4:** Account provisioning logic.
    - If the Google email *does not exist* in the `User` table: Create a new active user. Since the password field might be required by the existing DB schema, generate a secure, random cryptographic hash for the password, or adapt the schema to make the password nullable for OAuth users.
    - If the Google email *already exists*: Authenticate the user.
- [ ] **AC5:** JWT Issuance. Upon successful provisioning or authentication (AC4), the callback endpoint must issue and return the native application JWT so the frontend can manage the session exactly as it does with standard email/password logins.
- [ ] **AC6:** Test coverage. Create unit tests for the new endpoints, mocking the external HTTP calls to the Google API to ensure the testing environment remains isolated and deterministic.

## 4. Implementation Notes
- Consider using a robust library like `authlib` or `httpx` to handle the OAuth2 token exchange and API requests.
- Pay special attention to CORS and redirection flows between the React/Vite frontend (`FRONTEND_HOST`) and the FastAPI backend. The callback might need to redirect the user back to the frontend with the JWT securely attached (e.g., via a short-lived secure cookie or a structured redirect URI).
- Review the existing `user` CRUD operations in the Tiangolo template to ensure the newly created Google users have the correct default privileges (e.g., `is_superuser=False`, `is_active=True`).