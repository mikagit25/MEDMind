/**
 * Scenario 3: NCLEX demo (free, unlocked): start → submit immediately → result shown.
 *
 * The exam session is 10 questions across multiple NGN types (MCQ, ordered, SATA, calculation).
 * Rather than trying to answer questions (which requires type-specific handling), we:
 *   1. Click "Start Exam" on the unlocked demo mode card
 *   2. Click "Submit" in the exam header (opens confirmation modal)
 *   3. Click "Submit" inside the modal to finalize the session
 *   4. Assert the results page renders a score card (font class text-6xl on the score)
 *
 * Note: App layout renders {children} twice (mobile + desktop).
 * Selectors are scoped to "main" (desktop) or "div.fixed" (modal overlay).
 */
import { test, expect } from "@playwright/test";
import { loginAPI } from "./helpers";

test("nclex demo: start → submit → result", async ({ page }) => {
  await loginAPI(page);
  await page.goto("/exam");
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(2_000);

  // Scroll the main container to reveal all mode cards
  await page.evaluate(() => {
    const m = document.querySelector("main");
    if (m) m.scrollTo(0, m.scrollHeight);
  });
  await page.waitForTimeout(500);

  // Click "Start Exam" on the unlocked demo mode — scope to main
  const startBtn = page
    .locator("main button")
    .filter({ hasText: /^Start Exam$/ })
    .first();
  await expect(startBtn).toBeVisible({ timeout: 10_000 });
  await startBtn.click();

  // Wait for exam session to load (questions appear)
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(2_000);

  // The exam header has a "Submit" button — click it to open the confirmation modal
  // This button has a small text-xs style and bg-ink text-white class
  const submitHeaderBtn = page
    .locator("main button")
    .filter({ hasText: /^submit$/i })
    .first();
  await expect(submitHeaderBtn).toBeVisible({ timeout: 10_000 });
  await submitHeaderBtn.click();

  // Confirmation modal appears (fixed overlay): "Submit exam?" with Submit + Continue Exam buttons
  const modalSubmitBtn = page
    .locator("div.fixed button")
    .filter({ hasText: /^submit$/i })
    .first();
  await expect(modalSubmitBtn).toBeVisible({ timeout: 5_000 });
  await modalSubmitBtn.click();

  // Results page renders — the large score percentage uses class text-6xl (unique to score card)
  await expect(page.locator("main .text-6xl").first()).toBeVisible({ timeout: 20_000 });

  // Also verify the passed/not-passed verdict text is visible
  await expect(
    page.locator("main").getByText(/passed|not passed/i).first()
  ).toBeVisible({ timeout: 5_000 });
});
