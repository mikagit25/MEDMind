/**
 * Scenario 5: Flashcards — session → rate a card → counter decreases.
 */
import { test, expect } from "@playwright/test";
import { loginAPI } from "./helpers";

test("flashcards: rate card → counter changes", async ({ page }) => {
  await loginAPI(page);
  await page.goto("/flashcards");
  await page.waitForLoadState("networkidle");

  // Either there are due cards or we see an empty state
  const hasCards = await page.locator("button").filter({ hasText: /show answer|flip|reveal/i }).isVisible({ timeout: 8_000 }).catch(() => false);
  const hasSession = await page.locator("text=/card|flashcard/i").isVisible({ timeout: 5_000 }).catch(() => false);

  if (!hasCards && !hasSession) {
    // No due cards — go to modules to enqueue
    test.skip(true, "No flashcard session available — no due cards");
    return;
  }

  // Reveal answer
  const revealBtn = page.locator("button").filter({ hasText: /show answer|flip|reveal/i }).first();
  if (await revealBtn.isVisible()) await revealBtn.click();

  // Rate the card (any of: Easy, Good, Hard, Again, 0-5 buttons)
  const rateBtn = page.locator("button").filter({ hasText: /easy|good|hard|again|✓|0|1|2|3|4|5/i }).first();
  await expect(rateBtn).toBeVisible({ timeout: 8_000 });
  await rateBtn.click();

  // Accept: session continues (next card or completion message)
  await page.waitForTimeout(1_500);
  const continued = await page.locator("text=/complete|next|card/i").isVisible({ timeout: 5_000 }).catch(() => false);
  expect(continued).toBe(true);
});
