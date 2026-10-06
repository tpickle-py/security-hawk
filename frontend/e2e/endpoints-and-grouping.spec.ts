import { test, expect } from "@playwright/test";
import { setupMockApi } from "./helpers/mockApi";

test.describe("Endpoints Dragging, Moving & Grouping Workflows", () => {
  test.beforeEach(async ({ page }) => {
    page.on("console", (msg) => console.log("BROWSER:", msg.text()));
    await setupMockApi(page);
    await page.goto("/");
  });

  test("Clicking an endpoint selects it and opens PropertyPanel", async ({ page }) => {
    const endpoint = page.locator(".endpoint-icon-group").first();
    await expect(endpoint).toBeVisible();

    await endpoint.click();
    await expect(endpoint).toHaveClass(/selected/);

    // PropertyPanel opens
    const propPanel = page.locator(".property-panel");
    await expect(propPanel).toBeVisible();
    await expect(propPanel).toContainText("Server Cam");
  });

  test("Shift-clicking multiple endpoints allows multi-selection", async ({ page }) => {
    const endpoints = page.locator(".endpoint-icon-group");
    await expect(endpoints.first()).toBeVisible();

    const count = await endpoints.count();
    console.log("ENDPOINT COUNT IN TEST:", count);

    // Select first endpoint
    await endpoints.nth(0).click({ force: true });

    // Shift-click second endpoint
    await page.keyboard.down("Shift");
    await endpoints.nth(1).click({ force: true });
    await page.keyboard.up("Shift");

    // Both should have selected class
    await expect(endpoints.nth(0)).toHaveClass(/selected/);
    await expect(endpoints.nth(1)).toHaveClass(/selected/);

    // PropertyPanel shows multi-selection header
    const propPanel = page.locator(".property-panel");
    await expect(propPanel).toContainText("2 items");
  });

  test("Grouping multiple endpoints creates a logical unit with 'G' badge", async ({ page }) => {
    const endpoints = page.locator(".endpoint-icon-group");
    await endpoints.nth(0).click({ force: true });
    await page.keyboard.down("Shift");
    await endpoints.nth(1).click({ force: true });
    await page.keyboard.up("Shift");

    const propPanel = page.locator(".property-panel");
    await expect(propPanel).toContainText("Group Into Unit");

    // Enter unit name and group
    const groupInput = propPanel.locator('input[placeholder*="Master Suite"]');
    await groupInput.fill("Core Cluster");
    await propPanel.locator("button").filter({ hasText: "Group as Single Unit" }).click();

    // Endpoints now display 'G' badge in SVG
    const groupBadges = page.locator(".endpoint-icon-group text").filter({ hasText: "G" });
    await expect(groupBadges).toHaveCount(2);

    // Contextual chip in CAD command line should now show 'Ungroup' when opened
    await page.keyboard.press("/");
    await expect(page.locator(".cad-chip-btn").filter({ hasText: "Ungroup" })).toBeVisible();
  });

  test("Ungrouping endpoints removes 'G' badge", async ({ page }) => {
    const endpoints = page.locator(".endpoint-icon-group");
    await endpoints.nth(0).click({ force: true });
    await page.keyboard.down("Shift");
    await endpoints.nth(1).click({ force: true });
    await page.keyboard.up("Shift");

    const propPanel = page.locator(".property-panel");
    await propPanel.locator("button").filter({ hasText: "Group as Single Unit" }).click();

    // Verify badges appeared
    await expect(page.locator(".endpoint-icon-group text").filter({ hasText: "G" })).toHaveCount(2);

    // Click Ungroup
    await propPanel.locator("button").filter({ hasText: "Ungroup Selected Items" }).click();

    // Badges should be removed
    await expect(page.locator(".endpoint-icon-group text").filter({ hasText: "G" })).toHaveCount(0);
  });

  test("Moving an endpoint updates its position", async ({ page }) => {
    const ep = page.locator(".endpoint-icon-group").first();
    const initialTransform = await ep.getAttribute("transform");

    const box = await ep.boundingBox();
    if (!box) throw new Error("Endpoint bounding box not found");

    // Drag endpoint by 80px horizontally
    await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
    await page.mouse.down();
    await page.mouse.move(box.x + box.width / 2 + 80, box.y + box.height / 2 + 50, { steps: 5 });
    await page.mouse.up();

    const newTransform = await ep.getAttribute("transform");
    expect(newTransform).not.toEqual(initialTransform);
  });
});
