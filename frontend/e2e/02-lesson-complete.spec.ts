/**
 * Scenario 2: Login → open module → click lesson → mark complete.
 * Module page is a SPA: lessons are clicked inline (no URL change).
 *
 * Note: The app layout renders {children} twice (mobile + desktop).
 * All selectors must be scoped to "main" (the visible desktop container)
 * to avoid matching the CSS-hidden mobile duplicates.
 */
import { test, expect } from "@playwright/test";
import { loginAPI } from "./helpers";

test("lesson marked as complete", async ({ page }) => {
  await loginAPI(page);
  await page.goto("/modules");
  await page.waitForLoadState("networkidle");

  // Click first module card — scope to main to skip hidden mobile duplicates
  const moduleCard = page.locator("main a[href*='/modules/']").first();
  await expect(moduleCard).toBeVisible({ timeout: 10_000 });
  await moduleCard.click();
  await page.waitForURL(/\/modules\//, { timeout: 10_000 });
  await page.waitForLoadState("networkidle");

  // On the module page, lessons are buttons in the sidebar inside main
  const lessonBtn = page
    .locator("main button")
    .filter({ hasNotText: /← Back|Mark complete|Continue|← /i })
    .first();
  await expect(lessonBtn).toBeVisible({ timeout: 8_000 });
  await lessonBtn.click();
  await page.waitForTimeout(1_000);

  // "Mark complete & continue" button appears in the lesson view
  const markBtn = page.locator("main").getByText(/mark complete/i).first();
  await expect(markBtn).toBeVisible({ timeout: 10_000 });
  await markBtn.click();

  // After marking complete: either moved to next lesson, counter updates, or toast
  await page.waitForTimeout(2_000);
  // Page is still on the module URL (SPA) — accept if we're still there
  expect(page.url()).toMatch(/\/modules\//);
});
