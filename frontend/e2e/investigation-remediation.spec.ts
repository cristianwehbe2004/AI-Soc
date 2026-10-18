import { expect, test } from "@playwright/test";

test("investigation displays a remediation plan and links to response actions", async ({ page }) => {
  await page.route("**/api/v1/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith("/auth/refresh")) {
      await route.fulfill({ json: {
        access_token: "browser-test-session", token_type: "bearer", expires_in: 900,
        user: { id: "analyst-browser-test", email: "analyst@example.test", full_name: "Test Analyst", role_name: "analyst", is_active: true },
      } });
    } else if (path.endsWith("/investigations/browser-example")) {
      await route.fulfill({ json: {
        id: "browser-example", incident_id: "incident-example", status: "completed",
        provider: "mock", model: "browser-example", validation_errors: [],
        result: {
          executive_summary: "Reported network exposure needs verification",
          attack_story: "An analyst reported an allowed inbound management connection.",
          confidence: 0.6, findings: [], evidence_gaps: ["Verify the affected resource with its owner"],
          risk_analysis: { score: 70, severity: "high", rationale: "Reported management access", factors: [] },
          mitre_context: [], recommendations: [{
            title: "Restrict the reported path", priority: "high", rationale: "Review the intended access policy.",
            actions: ["Review the access rule"], evidence_refs: ["evidence:firewall-observation"],
            remediation_plan: {
              verification_steps: ["Confirm the firewall observation and asset identity"],
              change_steps: ["Limit access to approved administrator sources"],
              validation_steps: ["Check blocked unauthorized access and successful approved access"],
              rollback_steps: ["Restore approved configuration if business traffic fails"],
              impact: "Remote administrator connections may be interrupted",
            },
          }],
        },
      } });
    } else {
      await route.fulfill({ status: 503, json: { detail: "Unavailable in this isolated browser test" } });
    }
  });

  await page.goto("/investigations/browser-example");
  const plan = page.getByRole("region", { name: "Remediation plan" });
  await expect(plan).toBeVisible();
  for (const heading of ["Verify the weakness", "Apply the fix", "Check the outcome", "Rollback if needed"]) {
    await expect(plan.getByRole("heading", { name: heading })).toBeVisible();
  }
  await expect(plan).toContainText("Remote administrator connections may be interrupted");
  await expect(page.getByText("Sources: evidence:firewall-observation")).toBeVisible();
  await expect(page.getByRole("link", { name: "Open response actions" })).toHaveAttribute("href", "/incidents/incident-example#response-actions");
});
