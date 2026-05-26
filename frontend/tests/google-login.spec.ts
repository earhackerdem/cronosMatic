import { expect, test } from "@playwright/test"

// Note: read from process.env (not import.meta.env) because Playwright runs in
// Node. playwright.config.ts loads the project root .env via `dotenv/config`,
// which surfaces VITE_* vars to this scope. The Vite client picks up the same
// variable at build/dev startup, so both sides see the same value.
const googleLoginEnabled = process.env.VITE_GOOGLE_LOGIN_ENABLED === "true"

test.use({ storageState: { cookies: [], origins: [] } })

const FAKE_JWT = "fake.jwt.token"

// Always runs in both flag states. Asserts that the button presence in the DOM
// tracks the env var — covers task 8.2 directly (button hidden when flag off).
test("Google login button visibility matches VITE_GOOGLE_LOGIN_ENABLED", async ({
  page,
}) => {
  for (const path of ["/login", "/signup"]) {
    await page.goto(path)
    const button = page.getByTestId("google-login-button")
    if (googleLoginEnabled) {
      await expect(button).toBeVisible()
      await expect(button).toHaveAccessibleName(/Continue with Google/i)
    } else {
      await expect(button).toHaveCount(0)
    }
  }
})

test("Clicking Google button navigates to backend login endpoint", async ({
  page,
}) => {
  test.skip(
    !googleLoginEnabled,
    "Button not rendered when VITE_GOOGLE_LOGIN_ENABLED is not 'true'",
  )
  // Intercept the backend redirect target so we never reach real Google.
  await page.route("**/api/v1/auth/google/login", (route) => {
    route.fulfill({ status: 204, body: "" })
  })

  await page.goto("/login")
  const navigation = page.waitForRequest("**/api/v1/auth/google/login")
  await page.getByTestId("google-login-button").click()
  const request = await navigation
  expect(request.url()).toContain("/api/v1/auth/google/login")
})

// The /auth/callback route is registered regardless of the build-time flag —
// these tests exercise the route logic directly and run in both flag states.

test("/auth/callback with access_token stores token and lands on /", async ({
  page,
}) => {
  // Stub /users/me so the JWT (which the backend can't verify) doesn't
  // trigger the global 401 handler that would clear the token + bounce
  // us back to /login. We are testing the callback's token capture, not
  // the dashboard's auth gate.
  await page.route("**/api/v1/users/me", (route) => {
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: "00000000-0000-0000-0000-000000000000",
        email: "google-user@example.com",
        full_name: "Google User",
        is_active: true,
        is_superuser: false,
      }),
    })
  })

  await page.goto(`/auth/callback?access_token=${FAKE_JWT}`)
  await page.waitForURL("/")
  const stored = await page.evaluate(() =>
    localStorage.getItem("access_token"),
  )
  expect(stored).toBe(FAKE_JWT)
})

test("/auth/callback with error shows toast and lands on /login", async ({
  page,
}) => {
  await page.goto("/auth/callback?error=access_denied")
  await page.waitForURL((url) => url.pathname === "/login")
  await expect(page.getByText(/Google login failed/i)).toBeVisible()
  const stored = await page.evaluate(() =>
    localStorage.getItem("access_token"),
  )
  expect(stored).toBeNull()
})

test("/auth/callback with no params lands on /login with no toast", async ({
  page,
}) => {
  await page.goto("/auth/callback")
  await page.waitForURL((url) => url.pathname === "/login")
  await expect(page.getByText(/Google login failed/i)).toHaveCount(0)
})
