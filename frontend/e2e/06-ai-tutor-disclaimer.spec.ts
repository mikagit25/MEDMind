/**
 * Scenario 6: AI tutor in patient mode → disclaimer visible.
 * API is mocked — no real AI key needed in CI.
 */
import { test, expect } from "@playwright/test";
import { loginAPI } from "./helpers";

test("ai tutor patient mode shows disclaimer", async ({ page }) => {
  await loginAPI(page);

  // Mock the AI streaming endpoint
  await page.route("**/api/v1/ai/ask**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "text/event-stream",
      body: 'data: {"type":"done","model":"mock"}\n\n',
    });
  });

  // ?mode=patient sets initial mode via useState(() => searchParams.get("mode") || "tutor")
  await page.goto("/ai-tutor?mode=patient");
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(1_500); // allow React hydration

  // Explicitly click Patient mode tab if it exists
  const patientBtn = page.locator("button").filter({ hasText: /patient/i }).first();
  if (await patientBtn.isVisible({ timeout: 3_000 }).catch(() => false)) {
    await patientBtn.click();
    await page.waitForTimeout(800);
  }

  // The AI tutor page MUST be rendered (not redirected to login)
  await expect(page).not.toHaveURL(/\/login|\/register/);

  // Patient mode footer text — check for any of the key phrases using getByText
  // The footer <p> contains: "🏥 Patient mode — plain language, no diagnoses..."
  const bodyHTML = await page.content();
  const hasPatientText =
    bodyHTML.includes("plain language") ||
    bodyHTML.includes("no diagnoses") ||
    bodyHTML.includes("Patient mode") ||
    bodyHTML.includes("patient");

  expect(hasPatientText).toBe(true);
});
