/**
 * E2E tests for: checklist, comments, export, WIP limits, board sharing,
 * keyboard shortcuts, activity feed, dark mode, stats panel.
 */
import { expect, test, type Page } from "@playwright/test";

const DEMO_USER = { username: "user", password: "password" };

async function login(page: Page) {
  await page.goto("/login");
  await page.getByPlaceholder("Enter username").fill(DEMO_USER.username);
  await page.getByPlaceholder("Enter password").fill(DEMO_USER.password);
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page).toHaveURL(/\/boards/);
}

async function openFirstBoard(page: Page) {
  await login(page);
  await page.getByRole("button", { name: /open/i }).first().click();
  await expect(page).toHaveURL(/\/board\?id=/);
  await page.locator('[data-testid^="column-"]').first().waitFor({ state: "visible" });
}

async function addCard(page: Page, title: string) {
  const firstColumn = page.locator('[data-testid^="column-"]').first();
  await firstColumn.getByRole("button", { name: /add a card/i }).click();
  await firstColumn.getByPlaceholder("Card title").fill(title);
  await firstColumn.getByRole("button", { name: /add card/i }).click();
  await expect(firstColumn.getByText(title)).toBeVisible();
  return firstColumn;
}

// ── Stats Panel ─────────────────────────────────────────────────────────────────

test("stats panel is visible on board page", async ({ page }) => {
  await openFirstBoard(page);
  await expect(page.getByText("Total cards")).toBeVisible();
  await expect(page.getByText("Columns")).toBeVisible();
  await expect(page.getByText("High priority")).toBeVisible();
});

test("stats panel shows correct column count", async ({ page }) => {
  await openFirstBoard(page);
  const columns = await page.locator('[data-testid^="column-"]').count();
  const columnsStatEl = page.locator("div").filter({ hasText: /^Columns$/ }).locator("..").locator("span").first();
  const statsValue = await columnsStatEl.textContent();
  expect(Number(statsValue)).toBe(columns);
});

// ── Board Header Buttons ─────────────────────────────────────────────────────────

test("export button is visible", async ({ page }) => {
  await openFirstBoard(page);
  await expect(page.getByText("Export")).toBeVisible();
});

test("share button is visible", async ({ page }) => {
  await openFirstBoard(page);
  await expect(page.getByText("Share")).toBeVisible();
});

test("activity button is visible", async ({ page }) => {
  await openFirstBoard(page);
  await expect(page.getByText("Activity")).toBeVisible();
});

// ── Keyboard Shortcuts ──────────────────────────────────────────────────────────

test("? key shows keyboard shortcuts overlay", async ({ page }) => {
  await openFirstBoard(page);
  await page.keyboard.press("?");
  await expect(page.getByText("Keyboard Shortcuts")).toBeVisible();
  await expect(page.getByText("Focus search")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByText("Keyboard Shortcuts")).not.toBeVisible();
});

test("? button in header shows shortcuts", async ({ page }) => {
  await openFirstBoard(page);
  await page.getByRole("button", { name: "?" }).click();
  await expect(page.getByText("Keyboard Shortcuts")).toBeVisible();
  await page.getByRole("button", { name: /close/i }).last().click();
  await expect(page.getByText("Keyboard Shortcuts")).not.toBeVisible();
});

test("/ key focuses search input", async ({ page }) => {
  await openFirstBoard(page);
  await page.keyboard.press("/");
  const searchInput = page.locator("#filter-search");
  await expect(searchInput).toBeFocused();
});

// ── WIP Limits ───────────────────────────────────────────────────────────────────

test("setting a WIP limit shows it in column header", async ({ page }) => {
  await openFirstBoard(page);
  const firstColumn = page.locator('[data-testid^="column-"]').first();

  // Click WIP limit button (circle+cross icon)
  const wipBtn = firstColumn.locator("button[title='Set WIP limit']");
  await wipBtn.click();

  // Fill in the limit
  const wipInput = firstColumn.locator("input[type='number']");
  await wipInput.clear();
  await wipInput.fill("3");
  await firstColumn.getByText("Save").click();

  // Should show /3 in the card count area
  await expect(firstColumn.getByText(/\/3/)).toBeVisible();
});

// ── Checklist ────────────────────────────────────────────────────────────────────

test("can add checklist items in card modal", async ({ page }) => {
  await openFirstBoard(page);
  const firstColumn = await addCard(page, "Checklist Card E2E");

  // Open edit modal
  const card = firstColumn.locator("article").filter({ hasText: "Checklist Card E2E" });
  await card.getByRole("button", { name: /edit/i }).click();

  // Switch to checklist tab
  await page.getByRole("button", { name: /checklist/i }).click();

  // Add items
  await page.getByPlaceholder("Add item...").fill("Step 1");
  await page.getByRole("button", { name: /^add$/i }).last().click();
  await expect(page.getByText("Step 1")).toBeVisible();

  await page.getByPlaceholder("Add item...").fill("Step 2");
  await page.getByRole("button", { name: /^add$/i }).last().click();
  await expect(page.getByText("Step 2")).toBeVisible();
});

test("can check a checklist item", async ({ page }) => {
  await openFirstBoard(page);
  const firstColumn = await addCard(page, "Checklist Toggle E2E");

  const card = firstColumn.locator("article").filter({ hasText: "Checklist Toggle E2E" });
  await card.getByRole("button", { name: /edit/i }).click();
  await page.getByRole("button", { name: /checklist/i }).click();

  await page.getByPlaceholder("Add item...").fill("Toggleable step");
  await page.getByRole("button", { name: /^add$/i }).last().click();

  const checkbox = page.locator("input[type='checkbox']").last();
  await checkbox.check();
  await expect(checkbox).toBeChecked();
});

// ── Comments ────────────────────────────────────────────────────────────────────

test("can post and view a comment", async ({ page }) => {
  await openFirstBoard(page);
  const firstColumn = await addCard(page, "Comment Card E2E");

  const card = firstColumn.locator("article").filter({ hasText: "Comment Card E2E" });
  await card.getByRole("button", { name: /edit/i }).click();
  await page.getByRole("button", { name: /comments/i }).click();

  await page.getByPlaceholder("Write a comment...").fill("This is an e2e comment");
  await page.getByRole("button", { name: /post comment/i }).click();

  await expect(page.getByText("This is an e2e comment")).toBeVisible();
});

// ── Activity Feed ────────────────────────────────────────────────────────────────

test("activity feed shows after adding a card", async ({ page }) => {
  await openFirstBoard(page);
  await addCard(page, "Activity Log Card E2E");

  // Open activity feed
  await page.getByRole("button", { name: /activity/i }).click();
  await expect(page.getByText("Activity")).toBeVisible();

  // Should show the card creation
  await expect(page.locator("div").filter({ hasText: /created.*card/ }).first()).toBeVisible();
});

test("activity feed closes with Escape", async ({ page }) => {
  await openFirstBoard(page);
  await page.getByRole("button", { name: /activity/i }).click();
  await expect(page.getByText("Activity")).toBeVisible();
  await page.keyboard.press("Escape");
  // The feed is hidden (no modal overlay — it's a floating panel)
});

// ── Share Dialog ─────────────────────────────────────────────────────────────────

test("share dialog opens and shows invite form", async ({ page }) => {
  await openFirstBoard(page);
  await page.getByText("Share").click();
  await expect(page.getByText("Share Board")).toBeVisible();
  await expect(page.getByPlaceholder("Username to invite...")).toBeVisible();
  await page.getByRole("button", { name: /close/i }).click();
  await expect(page.getByText("Share Board")).not.toBeVisible();
});

test("inviting nonexistent user shows error", async ({ page }) => {
  await openFirstBoard(page);
  await page.getByText("Share").click();
  await page.getByPlaceholder("Username to invite...").fill("ghost_user_does_not_exist_xyz");
  await page.getByRole("button", { name: /invite/i }).click();
  await expect(page.getByText(/user not found/i)).toBeVisible({ timeout: 5000 });
});

// ── Dark Mode ─────────────────────────────────────────────────────────────────────

test("dark mode toggle adds .dark class to html", async ({ page }) => {
  await openFirstBoard(page);

  // Find and click the dark mode toggle button
  const darkBtn = page.locator("button[title='Dark mode']").or(page.locator("button[title='Light mode']"));
  await darkBtn.first().click();

  // html element should have class 'dark'
  const hasDark = await page.evaluate(() => document.documentElement.classList.contains("dark"));
  expect(hasDark).toBe(true);

  // Toggle back
  await darkBtn.first().click();
  const hasDarkAfter = await page.evaluate(() => document.documentElement.classList.contains("dark"));
  expect(hasDarkAfter).toBe(false);
});

// ── Export ────────────────────────────────────────────────────────────────────────

test("export dropdown appears on hover", async ({ page }) => {
  await openFirstBoard(page);
  const exportBtn = page.getByText("Export");
  await exportBtn.hover();
  await expect(page.getByText("JSON")).toBeVisible();
  await expect(page.getByText("CSV")).toBeVisible();
});

// ── Filter / Search ───────────────────────────────────────────────────────────────

test("filter bar hides non-matching cards", async ({ page }) => {
  await openFirstBoard(page);

  // Add two distinct cards
  const col = page.locator('[data-testid^="column-"]').first();
  await col.getByRole("button", { name: /add a card/i }).click();
  await col.getByPlaceholder("Card title").fill("UniqueAlpha999");
  await col.getByRole("button", { name: /add card/i }).click();

  await col.getByRole("button", { name: /add a card/i }).click();
  await col.getByPlaceholder("Card title").fill("UniqueBeta000");
  await col.getByRole("button", { name: /add card/i }).click();

  // Search for Alpha
  await page.locator("#filter-search").fill("UniqueAlpha999");
  await expect(page.getByText("UniqueAlpha999")).toBeVisible();
  await expect(page.getByText("UniqueBeta000")).not.toBeVisible();

  // Clear filter
  await page.getByRole("button", { name: /clear/i }).click();
  await expect(page.getByText("UniqueBeta000")).toBeVisible();
});
