/**
 * Scenario 10: Language switch en → ru — interface updates, key pages don't crash.
 */
import { test, expect } from "@playwright/test";

test("language switch en→ru: interface updates", async ({ page }) => {
  await page.goto("/");
  await page.waitForLoadState("networkidle");

  // Find the language selector (a <select> with locale options)
  const langSelect = page.locator("select").filter({ has: page.locator("option[value='ru']") }).first();
  await expect(langSelect).toBeVisible({ timeout: 8_000 });

  // Switch to Russian
  await langSelect.selectOption("ru");
  await page.waitForTimeout(1_000);

  // The page should now contain some Russian text (Cyrillic)
  const bodyText = await page.locator("body").innerText();
  const hasCyrillic = /[а-яА-ЯёЁ]/.test(bodyText);
  expect(hasCyrillic).toBe(true);

  // Articles page should still load (no crash)
  await page.goto("/articles");
  await page.waitForLoadState("networkidle");
  await expect(page).not.toHaveURL(/error|500/);
  // Page renders something (h1 or article cards)
  const hasContent = await page.locator("h1, article, [class*='article']").first().isVisible({ timeout: 10_000 }).catch(() => false);
  expect(hasContent).toBe(true);
});
