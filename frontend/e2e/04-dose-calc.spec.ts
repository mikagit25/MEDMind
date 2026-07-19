/**
 * Scenario 4: Dose-calc trainer — click Generate, answer, see step solution.
 *
 * Note: The app layout renders {children} twice (mobile + desktop).
 * All selectors must be scoped to "main" (the visible desktop container)
 * to avoid matching the CSS-hidden mobile duplicates.
 */
import { test, expect } from "@playwright/test";
import { loginAPI } from "./helpers";

test("dose-calc: problem → answer → step solution", async ({ page }) => {
  await loginAPI(page);
  await page.goto("/dose-calc");
  await page.waitForLoadState("networkidle");

  // "Generate Problem" button is the main CTA — scope to main
  const generateBtn = page.locator("main button").filter({ hasText: /generate problem/i }).first();
  await expect(generateBtn).toBeVisible({ timeout: 10_000 });
  await generateBtn.click();

  // Wait for the API to return the problem (deterministic, no AI — should be fast)
  await page.waitForTimeout(3_000);

  // The question text appears in a <p> element inside main; wait up to 15s for slow server
  const question = page
    .locator("main p")
    .filter({ hasText: /mg|mL|mcg|units|dose|patient|weight/i })
    .first();
  await expect(question).toBeVisible({ timeout: 15_000 });

  // Numeric answer input — scope to main
  const answerInput = page
    .locator('main input[type="number"], main input[type="text"][inputmode="decimal"], main input[type="text"][inputmode="numeric"]')
    .first();
  const anyInput = page.locator("main input:not([type='hidden'])").first();

  if (await answerInput.isVisible({ timeout: 5_000 }).catch(() => false)) {
    await answerInput.fill("5");
  } else {
    await expect(anyInput).toBeVisible({ timeout: 5_000 });
    await anyInput.fill("5");
  }

  // Check answer button — scope to main
  const checkBtn = page.locator("main button").filter({ hasText: /check|submit|confirm/i }).first();
  await checkBtn.click();

  // Result: "Step-by-Step Solution" or "Correct" / "Incorrect"
  const result = page.locator("main").getByText(/step-by-step|correct|incorrect/i).first();
  await expect(result).toBeVisible({ timeout: 10_000 });
});
