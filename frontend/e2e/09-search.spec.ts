/**
 * Scenario 9: Search — Ctrl+K → query → click result → navigate.
 */
import { test, expect } from "@playwright/test";
import { loginAPI } from "./helpers";

test("search: Ctrl+K opens modal, results navigate", async ({ page }) => {
  await loginAPI(page);
  await page.goto("/dashboard");
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(1_000);

  // Open global search via keyboard shortcut
  await page.keyboard.press("Control+k");

  // The GlobalSearch modal has a plain input with placeholder from i18n
  const searchInput = page.locator('input').filter({ hasNot: page.locator('[type="hidden"]') }).last();
  await expect(searchInput).toBeVisible({ timeout: 8_000 });

  // Type a query
  await searchInput.fill("cardio");
  await page.waitForTimeout(1_200); // debounce 300ms + network

  // Results are <button> elements inside <li> in <ul>
  const resultBtn = page.locator("ul li button").first();
  await expect(resultBtn).toBeVisible({ timeout: 8_000 });

  // Click the result — Playwright's click() fires pointerdown → mousedown → click
  // which triggers React's onMouseDown handler and router.push navigation
  await Promise.all([
    page.waitForNavigation({ waitUntil: "networkidle", timeout: 10_000 }).catch(() => null),
    resultBtn.click(),
  ]);

  // Should have navigated away from dashboard
  const url = page.url();
  expect(url).not.toContain("/dashboard");
  expect(url).toMatch(/\/(modules|articles|lessons|drugs|search)/);
});
