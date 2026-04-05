import { expect, test, type Page } from "@playwright/test";

/** Log in and navigate to the first board. Returns boardId. */
async function loginAndOpenBoard(page: Page): Promise<string> {
  await page.goto("/login");
  await page.getByPlaceholder("Enter username").fill("user");
  await page.getByPlaceholder("Enter password").fill("password");
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page).toHaveURL(/\/boards/);

  // Open the first board
  const firstOpenLink = page.getByRole("button", { name: /open/i }).first();
  await firstOpenLink.click();
  await expect(page).toHaveURL(/\/board\?id=/);

  // Extract boardId from URL
  const url = page.url();
  return url.split("id=")[1];
}

test("loads the kanban board with columns", async ({ page }) => {
  await loginAndOpenBoard(page);
  await expect(page.locator('[data-testid^="column-"]').first()).toBeVisible();
});

test("adds a card to a column", async ({ page }) => {
  await loginAndOpenBoard(page);
  const firstColumn = page.locator('[data-testid^="column-"]').first();
  await firstColumn.getByRole("button", { name: /add a card/i }).click();
  await firstColumn.getByPlaceholder("Card title").fill("Playwright card");
  await firstColumn.getByPlaceholder("Details").fill("Added via e2e.");
  await firstColumn.getByRole("button", { name: /add card/i }).click();
  await expect(firstColumn.getByText("Playwright card")).toBeVisible();
});

test("deletes a card", async ({ page }) => {
  await loginAndOpenBoard(page);
  const firstColumn = page.locator('[data-testid^="column-"]').first();

  // Add a card to delete
  await firstColumn.getByRole("button", { name: /add a card/i }).click();
  await firstColumn.getByPlaceholder("Card title").fill("Delete me");
  await firstColumn.getByRole("button", { name: /add card/i }).click();
  await expect(firstColumn.getByText("Delete me")).toBeVisible();

  // Delete it
  const card = firstColumn.locator("article").filter({ hasText: "Delete me" });
  await card.getByRole("button", { name: /delete/i }).click();
  await expect(firstColumn.getByText("Delete me")).not.toBeVisible();
});

test("opens card edit modal and saves changes", async ({ page }) => {
  await loginAndOpenBoard(page);
  const firstColumn = page.locator('[data-testid^="column-"]').first();

  // Add a card
  await firstColumn.getByRole("button", { name: /add a card/i }).click();
  await firstColumn.getByPlaceholder("Card title").fill("Edit test card");
  await firstColumn.getByRole("button", { name: /add card/i }).click();

  // Open edit modal
  const card = firstColumn.locator("article").filter({ hasText: "Edit test card" });
  await card.getByRole("button", { name: /edit/i }).click();

  // Change title
  const modal = page.locator('[role="none"]').filter({ hasText: "Edit Card" }).first()
    .or(page.locator("div").filter({ hasText: "Edit Card" }).last());
  await page.getByLabel("Title").or(page.locator('input[value="Edit test card"]')).fill("Updated title");
  await page.getByRole("button", { name: /save changes/i }).click();

  await expect(firstColumn.getByText("Updated title")).toBeVisible();
});

test("adds a new column to the board", async ({ page }) => {
  await loginAndOpenBoard(page);
  const before = await page.locator('[data-testid^="column-"]').count();

  await page.getByRole("button", { name: /\+ add column/i }).click();
  await page.getByPlaceholder("Column name...").fill("E2E Column");
  await page.getByRole("button", { name: /^add$/i }).click();

  await expect(page.locator('[data-testid^="column-"]')).toHaveCount(before + 1);
  await expect(page.getByText("E2E Column")).toBeVisible();
});

test("boards dashboard: create and delete a board", async ({ page }) => {
  await page.goto("/login");
  await page.getByPlaceholder("Enter username").fill("user");
  await page.getByPlaceholder("Enter password").fill("password");
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page).toHaveURL(/\/boards/);

  const countBefore = await page.locator('[class*="rounded-2xl"]').filter({ hasText: /Open/ }).count();

  await page.getByPlaceholder("New board name...").fill("Test Board Delete");
  await page.getByRole("button", { name: /create board/i }).click();
  await expect(page.getByText("Test Board Delete")).toBeVisible();

  // Delete the new board
  const newBoard = page.locator('div').filter({ hasText: /Test Board Delete/ }).last();
  await newBoard.getByRole("button", { name: /delete/i }).click();
  page.on("dialog", (dialog) => dialog.accept());
  await expect(page.getByText("Test Board Delete")).not.toBeVisible({ timeout: 5000 });
});

test("moves a card between columns", async ({ page }) => {
  await loginAndOpenBoard(page);
  const columns = page.locator('[data-testid^="column-"]');
  const firstColumn = columns.first();
  const secondColumn = columns.nth(1);

  // Add a card to first column
  await firstColumn.getByRole("button", { name: /add a card/i }).click();
  await firstColumn.getByPlaceholder("Card title").fill("Drag me");
  await firstColumn.getByRole("button", { name: /add card/i }).click();
  await expect(firstColumn.getByText("Drag me")).toBeVisible();

  // Drag from first to second column
  const card = firstColumn.locator("article").filter({ hasText: "Drag me" });
  const cardBox = await card.boundingBox();
  const colBox = await secondColumn.boundingBox();
  if (!cardBox || !colBox) throw new Error("Could not get bounding boxes");

  await page.mouse.move(cardBox.x + cardBox.width / 2, cardBox.y + cardBox.height / 2);
  await page.mouse.down();
  await page.mouse.move(colBox.x + colBox.width / 2, colBox.y + 80, { steps: 15 });
  await page.mouse.up();

  await expect(secondColumn.getByText("Drag me")).toBeVisible();
});
