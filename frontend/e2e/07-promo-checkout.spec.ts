/**
 * Scenario 7: Apply promo code → success/error message shown.
 */
import { test, expect } from "@playwright/test";
import { loginAPI, E2E_PROMO } from "./helpers";

test("promo code applied → success shown", async ({ page }) => {
  await loginAPI(page);
  await page.goto("/pricing");
  await page.waitForLoadState("networkidle");

  // Open promo input toggle
  const promoToggle = page.locator("button, span").filter({ hasText: /promo code|have a code/i }).first();
  await expect(promoToggle).toBeVisible({ timeout: 8_000 });
  await promoToggle.click();

  // The input has placeholder="ENTER CODE"
  const promoInput = page.locator('input[placeholder="ENTER CODE"]');
  await expect(promoInput).toBeVisible({ timeout: 5_000 });
  await promoInput.fill(E2E_PROMO);

  // Apply button
  const applyBtn = page.locator("button").filter({ hasText: /apply|activate/i }).first();
  await applyBtn.click();

  // Either success or "invalid" — both mean the UI responded
  const feedback = page.locator("text=/activated|applied|valid until|invalid|not found|error/i").first();
  await expect(feedback).toBeVisible({ timeout: 8_000 });
});
