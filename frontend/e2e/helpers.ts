import { Page } from "@playwright/test";

const BASE_URL = process.env.PLAYWRIGHT_BASE_URL || "http://localhost:3000";
// If NEXT_PUBLIC_API_URL is explicitly set, use it; otherwise derive from base URL.
// For production testing (PLAYWRIGHT_BASE_URL=https://medmind.pro), use the same
// host's /api/v1 path. For local dev (localhost:3000), hit backend on port 8000.
const API_URL =
  process.env.NEXT_PUBLIC_API_URL ??
  (BASE_URL.includes("localhost") ? "http://localhost:8000/api/v1" : `${BASE_URL}/api/v1`);

export const E2E_EMAIL = "e2e_test@example.com";
export const E2E_PASSWORD = "E2eTest1234!";
export const E2E_PROMO = "E2ETEST50";

/** Login via UI form and wait for dashboard. */
export async function loginUI(page: Page): Promise<void> {
  // Auth route group (auth) → URL is /login, not /auth/login
  await page.goto("/login");
  await page.locator('input[type="email"]').fill(E2E_EMAIL);
  await page.locator('input[type="password"]').fill(E2E_PASSWORD);
  await page.locator('button[type="submit"]').click();
  await page.waitForURL(/\/(dashboard|onboarding)/, { timeout: 15_000 });
}

/** Login via API and inject token into localStorage — fast, no UI interaction. */
export async function loginAPI(page: Page): Promise<void> {
  const resp = await page.request.post(`${API_URL}/auth/login`, {
    data: { email: E2E_EMAIL, password: E2E_PASSWORD },
  });
  if (!resp.ok()) {
    throw new Error(`Login API failed: ${resp.status()} ${await resp.text()}`);
  }
  const body = await resp.json();
  const accessToken: string = body.access_token;
  const refreshToken: string = body.refresh_token ?? "";
  const user = body.user;

  // Navigate to the landing page so localStorage is writeable for this origin
  await page.goto("/");
  await page.waitForLoadState("domcontentloaded");

  // Inject into all places the app reads auth state:
  // 1. Zustand persist key ("medmind-auth") — shape must match AuthState partialize
  // 2. Direct localStorage keys used by axios interceptor
  await page.evaluate(
    ({ accessToken, refreshToken, user }) => {
      const persistState = {
        state: {
          user,
          accessToken,
          refreshToken,
          isAuthenticated: true,
        },
        version: 0,
      };
      localStorage.setItem("medmind-auth", JSON.stringify(persistState));
      localStorage.setItem("access_token", accessToken);
      if (refreshToken) localStorage.setItem("refresh_token", refreshToken);
    },
    { accessToken, refreshToken, user }
  );
}
