import { expect, test } from "@playwright/test";

test("renders the credential-free login shell", async ({ page }) => {
  await page.route("**/api/v1/auth/refresh", async (route) => {
    await route.fulfill({
      status: 401,
      contentType: "application/json",
      body: JSON.stringify({ detail: "Not authenticated" }),
    });
  });

  await page.goto("/login");

  await expect(page).toHaveTitle(/AI-SOC/);
  await expect(page.getByRole("heading", { name: "Sign in to the console" })).toBeVisible();
  await expect(page.getByLabel("Email address")).toBeVisible();
  await expect(page.getByRole("button", { name: "Enter operations" })).toBeEnabled();
});
