import { expect, test } from "@playwright/test";

test("redirects unauthenticated users to /login", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveURL(/\/login/);
  await expect(page.getByRole("heading", { name: /project studio/i })).toBeVisible();
});

test("shows error on invalid credentials", async ({ page }) => {
  await page.goto("/login");
  await page.getByPlaceholder("Enter username").fill("wrong");
  await page.getByPlaceholder("Enter password").fill("wrong");
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page.getByText(/invalid credentials/i)).toBeVisible();
});

test("logs in with demo credentials and lands on boards page", async ({ page }) => {
  await page.goto("/login");
  await page.getByPlaceholder("Enter username").fill("user");
  await page.getByPlaceholder("Enter password").fill("password");
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page).toHaveURL(/\/boards/);
  await expect(page.getByText("My Boards")).toBeVisible();
});

test("shows register form when toggled", async ({ page }) => {
  await page.goto("/login");
  await page.getByRole("button", { name: /create account/i }).click();
  await expect(page.getByRole("button", { name: /create account/i }).last()).toBeVisible();
});

test("registers a new user and lands on boards page", async ({ page }) => {
  await page.goto("/login");
  await page.getByRole("button", { name: /create account/i }).click();
  const uniqueName = `e2euser_${Date.now()}`;
  await page.getByPlaceholder("Min 3 characters").fill(uniqueName);
  await page.getByPlaceholder("Min 6 characters").fill("securepass");
  await page.getByRole("button", { name: /create account/i }).last().click();
  await expect(page).toHaveURL(/\/boards/);
  await expect(page.getByText("My Boards")).toBeVisible();
});

test("logout returns to login page", async ({ page }) => {
  await page.goto("/login");
  await page.getByPlaceholder("Enter username").fill("user");
  await page.getByPlaceholder("Enter password").fill("password");
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page).toHaveURL(/\/boards/);
  await page.getByRole("button", { name: /sign out/i }).click();
  await expect(page).toHaveURL(/\/login/);
});
