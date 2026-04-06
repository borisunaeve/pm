/**
 * E2E tests for iteration 4 features:
 *   - Sprint panel (create, start, complete)
 *   - Analytics panel
 *   - Archive / restore cards
 *   - Global search overlay
 *   - Notifications bell
 *   - Board templates
 *   - Bulk select mode
 *   - Card history (activity) tab
 */
import { expect, test, type Page } from "@playwright/test";

const DEMO = { username: "user", password: "password" };

async function login(page: Page) {
  await page.goto("/login");
  await page.getByPlaceholder("Enter username").fill(DEMO.username);
  await page.getByPlaceholder("Enter password").fill(DEMO.password);
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
  const col = page.locator('[data-testid^="column-"]').first();
  await col.getByRole("button", { name: /add a card/i }).click();
  await col.getByPlaceholder("Card title").fill(title);
  await col.getByRole("button", { name: /add card/i }).click();
  await expect(col.getByText(title)).toBeVisible();
  return col;
}

// ── Sprint Panel ─────────────────────────────────────────────────────────────

test("sprint panel opens with Sprints button", async ({ page }) => {
  await openFirstBoard(page);
  await page.getByRole("button", { name: /sprints/i }).click();
  await expect(page.getByText("Sprints").last()).toBeVisible();
});

test("sprint panel opens with 's' key", async ({ page }) => {
  await openFirstBoard(page);
  await page.keyboard.press("s");
  await expect(page.getByText(/sprints/i).last()).toBeVisible();
});

test("sprint panel closes with Escape", async ({ page }) => {
  await openFirstBoard(page);
  await page.getByRole("button", { name: /sprints/i }).click();
  await expect(page.getByText("Sprints").last()).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByText("New Sprint")).not.toBeVisible();
});

test("can create a sprint from the panel", async ({ page }) => {
  await openFirstBoard(page);
  await page.getByRole("button", { name: /sprints/i }).click();

  await page.getByRole("button", { name: /new sprint/i }).click();
  await page.getByPlaceholder("e.g. Sprint 1").fill("E2E Sprint");
  await page.getByPlaceholder("What is the sprint goal?").fill("Ship the feature");
  await page.getByRole("button", { name: /create sprint/i }).click();

  await expect(page.getByText("E2E Sprint")).toBeVisible();
  await expect(page.getByText("Planning")).toBeVisible();
});

test("can start a sprint", async ({ page }) => {
  await openFirstBoard(page);
  await page.getByRole("button", { name: /sprints/i }).click();

  // Create sprint first
  await page.getByRole("button", { name: /new sprint/i }).click();
  const sprintName = `Sprint_${Date.now()}`;
  await page.getByPlaceholder("e.g. Sprint 1").fill(sprintName);
  await page.getByRole("button", { name: /create sprint/i }).click();
  await expect(page.getByText(sprintName)).toBeVisible();

  // Start it
  await page.getByRole("button", { name: /start sprint/i }).click();
  await expect(page.getByText("Active")).toBeVisible();
});

test("can complete an active sprint", async ({ page }) => {
  await openFirstBoard(page);
  await page.getByRole("button", { name: /sprints/i }).click();

  // Create + start sprint
  await page.getByRole("button", { name: /new sprint/i }).click();
  const sprintName = `Sprint_Complete_${Date.now()}`;
  await page.getByPlaceholder("e.g. Sprint 1").fill(sprintName);
  await page.getByRole("button", { name: /create sprint/i }).click();
  await page.getByRole("button", { name: /start sprint/i }).click();
  await expect(page.getByText("Active")).toBeVisible();

  // Complete it
  await page.getByRole("button", { name: /complete sprint/i }).click();
  await expect(page.getByText("Completed")).toBeVisible();
});

// ── Analytics Panel ──────────────────────────────────────────────────────────

test("analytics panel opens with Analytics button", async ({ page }) => {
  await openFirstBoard(page);
  await page.getByRole("button", { name: /analytics/i }).click();
  await expect(page.getByText("Board Analytics")).toBeVisible();
});

test("analytics panel opens with 'a' key", async ({ page }) => {
  await openFirstBoard(page);
  await page.keyboard.press("a");
  await expect(page.getByText("Board Analytics")).toBeVisible();
});

test("analytics panel shows overview stats", async ({ page }) => {
  await openFirstBoard(page);
  await page.getByRole("button", { name: /analytics/i }).click();
  await expect(page.getByText("Total Cards")).toBeVisible();
  await expect(page.getByText("Overdue")).toBeVisible();
  await expect(page.getByText("Archived")).toBeVisible();
  await expect(page.getByText("Due This Week")).toBeVisible();
});

test("analytics panel shows by-column breakdown", async ({ page }) => {
  await openFirstBoard(page);
  await page.getByRole("button", { name: /analytics/i }).click();
  await expect(page.getByText("Cards by Column")).toBeVisible();
});

test("analytics panel closes with Escape", async ({ page }) => {
  await openFirstBoard(page);
  await page.getByRole("button", { name: /analytics/i }).click();
  await expect(page.getByText("Board Analytics")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByText("Board Analytics")).not.toBeVisible();
});

// ── Archive / Restore ────────────────────────────────────────────────────────

test("archive button removes card from board view", async ({ page }) => {
  await openFirstBoard(page);
  const col = await addCard(page, "Archive E2E Card");

  const card = col.locator("article").filter({ hasText: "Archive E2E Card" });
  // Click archive (the polyline/box SVG button)
  await card.getByRole("button", { name: /archive/i }).click();
  await expect(col.getByText("Archive E2E Card")).not.toBeVisible({ timeout: 3000 });
});

test("archived cards appear when Archived toggle is on", async ({ page }) => {
  await openFirstBoard(page);
  const col = await addCard(page, "Toggle Archive Card");

  // Archive it
  const card = col.locator("article").filter({ hasText: "Toggle Archive Card" });
  await card.getByRole("button", { name: /archive/i }).click();
  await expect(col.getByText("Toggle Archive Card")).not.toBeVisible({ timeout: 3000 });

  // Toggle archived view
  await page.getByRole("button", { name: /archived/i }).click();
  await expect(page.getByText("Toggle Archive Card")).toBeVisible({ timeout: 5000 });
});

test("restore card makes it reappear in board", async ({ page }) => {
  await openFirstBoard(page);
  const col = await addCard(page, "Restore E2E Card");

  // Archive it
  const card = col.locator("article").filter({ hasText: "Restore E2E Card" });
  await card.getByRole("button", { name: /archive/i }).click();

  // Toggle archived, then restore
  await page.getByRole("button", { name: /archived/i }).click();
  await expect(page.getByText("Restore E2E Card")).toBeVisible({ timeout: 5000 });

  await page.getByRole("button", { name: /restore/i }).first().click();

  // Turn off archived view
  await page.getByRole("button", { name: /hide archived/i }).click();
  await expect(col.getByText("Restore E2E Card")).toBeVisible({ timeout: 5000 });
});

// ── Global Search Overlay ─────────────────────────────────────────────────────

test("Ctrl+K opens search overlay", async ({ page }) => {
  await openFirstBoard(page);
  await page.keyboard.press("Control+k");
  await expect(page.getByPlaceholder(/search cards/i)).toBeVisible();
});

test("search overlay finds card by title", async ({ page }) => {
  await openFirstBoard(page);
  const unique = `SearchTarget_${Date.now()}`;
  await addCard(page, unique);

  await page.keyboard.press("Control+k");
  await page.getByPlaceholder(/search cards/i).fill(unique);
  await expect(page.getByText(unique).last()).toBeVisible({ timeout: 5000 });
});

test("search overlay closes with Escape", async ({ page }) => {
  await openFirstBoard(page);
  await page.keyboard.press("Control+k");
  await expect(page.getByPlaceholder(/search cards/i)).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByPlaceholder(/search cards/i)).not.toBeVisible({ timeout: 2000 });
});

test("search button in header opens overlay", async ({ page }) => {
  await openFirstBoard(page);
  await page.getByRole("button", { name: /search/i }).click();
  await expect(page.getByPlaceholder(/search cards/i)).toBeVisible();
});

// ── Notifications Bell ────────────────────────────────────────────────────────

test("notifications bell is visible in board header", async ({ page }) => {
  await openFirstBoard(page);
  // Look for the bell button by its title
  await expect(page.locator("button[title='Due-date notifications']")).toBeVisible();
});

test("clicking bell opens notifications panel", async ({ page }) => {
  await openFirstBoard(page);
  await page.locator("button[title='Due-date notifications']").click();
  await expect(page.getByText("Notifications")).toBeVisible();
});

test("notifications panel closes when clicking Close", async ({ page }) => {
  await openFirstBoard(page);
  await page.locator("button[title='Due-date notifications']").click();
  await expect(page.getByText("Notifications")).toBeVisible();
  // Close button is inside the notification panel
  const panel = page.locator("div").filter({ hasText: /^Notifications$/ }).last();
  await panel.getByRole("button", { name: /close/i }).click();
  await expect(page.getByText("Notifications").last()).not.toBeVisible({ timeout: 2000 });
});

// ── Board Templates ───────────────────────────────────────────────────────────

test("can create a board with software template", async ({ page }) => {
  await login(page);
  const boardName = `SW_${Date.now()}`;

  await page.getByPlaceholder("New board name...").fill(boardName);
  await page.locator("select").selectOption("software");
  await page.getByRole("button", { name: /create board/i }).click();

  await expect(page.getByText(boardName)).toBeVisible();
  // Open the board and check for expected columns
  await page.getByRole("button", { name: /open/i }).last().click();
  await expect(page.getByText("Backlog")).toBeVisible();
  await expect(page.getByText("In Review")).toBeVisible();
  await expect(page.getByText("Testing")).toBeVisible();
});

test("can create a board with marketing template", async ({ page }) => {
  await login(page);
  const boardName = `MKT_${Date.now()}`;

  await page.getByPlaceholder("New board name...").fill(boardName);
  await page.locator("select").selectOption("marketing");
  await page.getByRole("button", { name: /create board/i }).click();

  await page.getByRole("button", { name: /open/i }).last().click();
  await expect(page.getByText("Ideas")).toBeVisible();
  await expect(page.getByText("Published")).toBeVisible();
});

test("can create a board with personal template", async ({ page }) => {
  await login(page);
  const boardName = `Personal_${Date.now()}`;

  await page.getByPlaceholder("New board name...").fill(boardName);
  await page.locator("select").selectOption("personal");
  await page.getByRole("button", { name: /create board/i }).click();

  await page.getByRole("button", { name: /open/i }).last().click();
  await expect(page.getByText("To Do")).toBeVisible();
  await expect(page.getByText("Doing")).toBeVisible();
});

// ── Bulk Select Mode ──────────────────────────────────────────────────────────

test("Select button enters multi-select mode", async ({ page }) => {
  await openFirstBoard(page);
  await page.getByRole("button", { name: /^select$/i }).click();
  // Multi-select mode shows checkboxes
  await expect(page.getByText(/select \(/i)).toBeVisible();
});

test("bulk select shows action toolbar when cards selected", async ({ page }) => {
  await openFirstBoard(page);
  await addCard(page, "Bulk Card E2E 1");

  await page.getByRole("button", { name: /^select$/i }).click();

  // Check the checkbox on the first card
  const col = page.locator('[data-testid^="column-"]').first();
  const checkbox = col.locator("input[type='checkbox']").first();
  await checkbox.check();

  // Should show bulk toolbar
  await expect(page.getByText(/1 selected/i)).toBeVisible();
  await expect(page.getByRole("button", { name: /archive/i }).last()).toBeVisible();
});

test("bulk archive removes selected cards", async ({ page }) => {
  await openFirstBoard(page);
  const col = await addCard(page, "Bulk Archive Target");

  await page.getByRole("button", { name: /^select$/i }).click();

  const checkbox = col.locator("input[type='checkbox']").last();
  await checkbox.check();

  // Click archive in toolbar
  const archiveBtn = page.getByRole("button", { name: /archive/i }).last();
  await archiveBtn.click();

  // Card should be gone
  await expect(col.getByText("Bulk Archive Target")).not.toBeVisible({ timeout: 5000 });
});

// ── Card History Tab ──────────────────────────────────────────────────────────

test("History tab shows in card edit modal", async ({ page }) => {
  await openFirstBoard(page);
  const col = await addCard(page, "History Tab Card");

  const card = col.locator("article").filter({ hasText: "History Tab Card" });
  await card.getByRole("button", { name: /edit/i }).click();

  await expect(page.getByRole("button", { name: /history/i })).toBeVisible();
});

test("History tab shows field change after edit", async ({ page }) => {
  await openFirstBoard(page);
  const col = await addCard(page, "History Change Card");

  // Open edit modal and change priority
  const card = col.locator("article").filter({ hasText: "History Change Card" });
  await card.getByRole("button", { name: /edit/i }).click();

  // Change priority from medium to high
  await page.locator("select").filter({ hasText: /low|medium|high/i }).selectOption("high");
  await page.getByRole("button", { name: /save changes/i }).click();

  // Reopen and go to History tab
  await card.getByRole("button", { name: /edit/i }).click();
  await page.getByRole("button", { name: /history/i }).click();

  // Should show the priority change
  await expect(page.getByText("priority")).toBeVisible();
  await expect(page.getByText("high")).toBeVisible();
});

test("History tab shows 'No changes' for new card", async ({ page }) => {
  await openFirstBoard(page);
  const col = await addCard(page, "Fresh Card No History");

  const card = col.locator("article").filter({ hasText: "Fresh Card No History" });
  await card.getByRole("button", { name: /edit/i }).click();
  await page.getByRole("button", { name: /history/i }).click();

  await expect(page.getByText(/no changes recorded/i)).toBeVisible();
});
