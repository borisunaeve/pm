import { expect, test } from "@playwright/test";

test("redirects unauthenticated users to /login", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveURL(/\/login/);
  await expect(page.getByRole("heading", { name: /kanban studio login/i })).toBeVisible();
});

test("shows error on invalid credentials", async ({ page }) => {
  await page.goto("/login");
  await page.getByPlaceholder("Enter username").fill("wrong");
  await page.getByPlaceholder("Enter password").fill("wrong");
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page.getByText(/invalid credentials/i)).toBeVisible();
});

test("logs in with valid credentials and lands on the board", async ({ page }) => {
  await page.goto("/login");
  await page.getByPlaceholder("Enter username").fill("user");
  await page.getByPlaceholder("Enter password").fill("password");
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page.getByRole("heading", { name: "Kanban Studio" })).toBeVisible();
});

test("logout returns to login page", async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("pm_auth", "true"));
  await page.goto("/");
  await page.getByRole("button", { name: /logout/i }).click();
  await expect(page).toHaveURL(/\/login/);
});
