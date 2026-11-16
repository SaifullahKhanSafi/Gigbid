import { test, expect, type Page } from "@playwright/test";

async function onboard(page: Page) {
  await page.goto("/");
  await page
    .getByRole("button", { name: "New here? Create an account" })
    .click();
  await page
    .getByLabel("Email address")
    .fill(
      `browser-${Date.now()}-${Math.random().toString(16).slice(2)}@example.test`,
    );
  await page
    .getByLabel("Password", { exact: true })
    .fill("browser-test-pass123");
  await page
    .getByRole("button", { name: "Create account", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Start with the way you work." }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Save & open inbox" }).click();
  await expect(
    page.getByRole("heading", { name: "Good work starts with a good fit." }),
  ).toBeVisible();
}
async function draft(page: Page) {
  await onboard(page);
  await page.goto("/jobs/demo-ml-0001");
  await page.getByRole("button", { name: "Analyze & draft" }).click();
  await expect(
    page.getByRole("button", { name: "Approve proposal", exact: true }),
  ).toBeEnabled();
}

test("onboarding saves persona and rate floor", async ({ page }) => {
  await onboard(page);
  await page.goto("/settings");
  await page.getByLabel("Portfolio persona").selectOption("data");
  await page.getByLabel("Minimum hourly rate (USD)").fill("35");
  await page.getByRole("button", { name: "Save preferences" }).click();
  await page.reload();
  await expect(page.getByLabel("Portfolio persona")).toHaveValue("data");
  await expect(page.getByLabel("Minimum hourly rate (USD)")).toHaveValue("35");
});
test("approval persists on refresh and sends once", async ({ page }) => {
  await draft(page);
  await page.reload();
  await expect(
    page.getByRole("button", { name: "Approve proposal", exact: true }),
  ).toBeEnabled();
  await page
    .getByRole("button", { name: "Approve proposal", exact: true })
    .click();
  await expect(page.locator(".page-heading .badge")).toHaveText("submitted");
  await page.goto("/messages");
  await expect(
    page.getByText(
      "Thank you. Could you explain your validation plan and suggest an interview time?",
    ),
  ).toBeVisible();
});
test("rejection stores a reason and never submits", async ({ page }) => {
  await draft(page);
  await page
    .getByLabel("Rejection reason")
    .fill("Scope does not match my availability.");
  await page.getByRole("button", { name: "Reject with reason" }).click();
  await expect(page.locator(".page-heading .badge")).toHaveText("rejected");
  await page.goto("/pipeline");
  await expect(
    page.locator(".kanban-column").nth(1).locator("h3"),
  ).toContainText("0");
});
test("editing requires checks and a fresh approval", async ({ page }) => {
  await draft(page);
  const editor = page.getByLabel("Proposal draft");
  await editor.fill(
    (await editor.inputValue()) + "\nCould you clarify the delivery timeline?",
  );
  await page.getByRole("button", { name: "Save edits & recheck" }).click();
  await expect(
    page.getByRole("button", { name: "Approve proposal", exact: true }),
  ).toBeEnabled();
  await page.reload();
  await expect(editor).toContainText("");
  await expect(editor).toHaveValue(/Could you clarify the delivery timeline/);
  await page
    .getByRole("button", { name: "Approve proposal", exact: true })
    .click();
  await expect(page.locator(".page-heading .badge")).toHaveText("submitted");
});
test("degraded mode banner explains saved work", async ({ page }) => {
  await onboard(page);
  await page.route("**/api/health", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        status: "ok",
        marketplace: "unavailable",
        mode: "local_sim",
        model_mode: "test",
      }),
    }),
  );
  await page.reload();
  await expect(page.getByRole("alert")).toContainText(
    "Marketplace unavailable. Work is saved",
  );
});
test("mobile inbox has no horizontal overflow", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await onboard(page);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
  await page.getByRole("button", { name: "Toggle navigation" }).click();
  await expect(
    page.getByRole("link", { name: "Settings", exact: true }),
  ).toBeVisible();
});
