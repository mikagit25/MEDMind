/**
 * Scenario 8: Public pages without auth — article → navigate → public quiz.
 */
import { test, expect } from "@playwright/test";

test("public contour: articles accessible without auth", async ({ page }) => {
  // Articles listing
  await page.goto("/articles");
  await page.waitForLoadState("networkidle");
  await expect(page).not.toHaveURL(/login/);

  // At least one article link present
  const articleLink = page.locator("a[href*='/articles/']").first();
  await expect(articleLink).toBeVisible({ timeout: 10_000 });
  await articleLink.click();

  await page.waitForLoadState("networkidle");
  // Article page must have an H1
  await expect(page.locator("h1").first()).toBeVisible({ timeout: 8_000 });
  // Not redirected to login
  expect(page.url()).not.toContain("/auth/login");
});

test("public contour: drugs page accessible without auth", async ({ page }) => {
  await page.goto("/drugs");
  await page.waitForLoadState("networkidle");
  await expect(page).not.toHaveURL(/login/);
  await expect(page.locator("h1").first()).toBeVisible({ timeout: 10_000 });
});

test("public contour: pricing page accessible without auth", async ({ page }) => {
  await page.goto("/pricing");
  await page.waitForLoadState("networkidle");
  await expect(page).not.toHaveURL(/login/);
});
