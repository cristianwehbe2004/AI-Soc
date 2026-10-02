import { expect, test } from "@playwright/test";

const email = process.env.E2E_EMAIL;
const password = process.env.E2E_PASSWORD;
const apiKey = process.env.E2E_API_KEY;

test("event ingestion appears in the live event feed", async ({ page, request }) => {
  test.skip(
    !email || !password || !apiKey,
    "Set E2E_EMAIL, E2E_PASSWORD, and E2E_API_KEY for the realtime acceptance flow",
  );

  await page.goto("/login");
  await page.getByLabel("Email address").fill(email!);
  await page.getByLabel("Password", { exact: true }).fill(password!);
  await page.getByRole("button", { name: "Enter operations" }).click();
  await expect(page).toHaveURL(/\/dashboard$/);

  await page.goto("/events");
  await expect(page.getByText("connected", { exact: true })).toBeVisible({ timeout: 10_000 });

  const eventId = `e2e-realtime-${Date.now()}`;
  const response = await request.post("/api/v1/events", {
    headers: { "X-API-Key": apiKey! },
    data: {
      event_id: eventId,
      timestamp: new Date().toISOString(),
      source: "e2e-realtime",
      source_type: "application",
      event_type: "login_success",
      category: "authentication",
      severity: "low",
      username: "realtime-test",
      source_ip: "203.0.113.44",
      status: "success",
      raw_payload: { test: "realtime" },
      metadata: { e2e: true },
    },
  });
  expect(response.status()).toBe(201);
  await expect(page.getByRole("button", { name: /1 new event/ })).toBeVisible({ timeout: 10_000 });
});