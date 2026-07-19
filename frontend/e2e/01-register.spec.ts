/**
 * Scenario 1: Register → onboarding → landing on start plan.
 * Uses a unique timestamp email so re-runs don't collide.
 */
import { test, expect } from "@playwright/test";

test("register → onboarding", async ({ page }) => {
  const email = `e2e_reg_${Date.now()}@example.com`;

  // Auth route group (auth) → URL is /register, not /auth/register
  await page.goto("/register");
  await expect(page).toHaveTitle(/MedMind|Register/i);

  // First / last name are type="text" with no placeholder
  const textInputs = page.locator('input[type="text"]');
  await textInputs.nth(0).fill("Test");
  await textInputs.nth(1).fill("User");
  await page.locator('input[type="email"]').fill(email);
  await page.locator('input[type="password"]').fill("E2eTest1234!");

  // Required consent checkboxes (first two: terms + data processing)
  const checkboxes = page.locator('input[type="checkbox"]');
  const count = await checkboxes.count();
  if (count >= 1) await checkboxes.nth(0).check();
  if (count >= 2) await checkboxes.nth(1).check();

  await page.locator('button[type="submit"]').click();

  // Should land on onboarding or dashboard
  await page.waitForURL(/\/(onboarding|dashboard)/, { timeout: 15_000 });
  expect(page.url()).toMatch(/\/(onboarding|dashboard)/);
});
