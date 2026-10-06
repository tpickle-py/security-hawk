import { test, expect } from "@playwright/test";
import { setupMockApi } from "./helpers/mockApi";

test.describe("Home Assistant Entities Panel & Smart Match UI/UX", () => {
  test.beforeEach(async ({ page }) => {
    await setupMockApi(page);
    await page.goto("/");
  });

  test("Entity Picker panel loads and displays tabs without overlap", async ({ page }) => {
    const entityPicker = page.locator(".entity-picker");
    await expect(entityPicker).toBeVisible();

    // Check tabs exist
    await expect(page.locator(".unassigned-tab-bar .tab-btn").filter({ hasText: "All" })).toBeVisible();
    await expect(page.locator(".unassigned-tab-bar .unassigned-btn")).toBeVisible();
    await expect(page.locator(".unassigned-tab-bar .rules-tab-btn")).toBeVisible();
  });

  test("Rules tab strictly isolates rules and does NOT bleed entity cards through", async ({ page }) => {
    // Click on Rules tab
    await page.locator(".rules-tab-btn").click();

    // Verify rules view is active
    await expect(page.locator(".rules-action-bar")).toBeVisible();
    await expect(page.locator(".rule-item").filter({ hasText: "Datacenter Intrusion Alarm" })).toBeVisible();

    // CRITICAL: Ensure NO physical entity cards bleed through into the rules tab
    const entityCardsInRules = page.locator(".entity-picker .entity-item:not(.rule-item)");
    await expect(entityCardsInRules).toHaveCount(0);
  });

  test("Unassigned tab shows Smart Match banner AND entity list beneath it", async ({ page }) => {
    // Click on Unassigned tab
    await page.locator(".unassigned-btn").click();

    // Verify Smart Match banner appears
    const banner = page.locator(".smart-match-banner");
    await expect(banner).toBeVisible();
    await expect(banner).toContainText("Smart Match Found");

    // Verify entity cards are visible beneath the banner (NOT blank / hidden)
    const entityItems = page.locator(".entity-picker .entity-list .entity-item");
    await expect(entityItems.first()).toBeVisible();
    await expect(entityItems).toHaveCount(3);
  });

  test("Domain filter filters entity list and updates Smart Match count", async ({ page }) => {
    await page.locator(".unassigned-btn").click();

    // Click 'Cameras' domain filter
    await page.locator(".filter-chip").filter({ hasText: "Cameras" }).click();

    // Verify only camera entities are displayed
    const entityItems = page.locator(".entity-picker .entity-list .entity-item");
    await expect(entityItems).toHaveCount(2);
    await expect(page.locator(".entity-picker")).toContainText("Living Room Wyze Cam");
    await expect(page.locator(".entity-picker")).toContainText("Datacenter Server Cam");
    await expect(page.locator(".entity-picker")).not.toContainText("Living Room PIR Motion");

    // Banner should reflect filtered cameras
    await expect(page.locator(".smart-match-banner")).toContainText("Cameras");
  });

  test("Area filter dropdown filters Smart Match and matches for selected room", async ({ page }) => {
    await page.locator(".unassigned-btn").click();

    // Select 'Datacenter' from Area dropdown
    await page.locator(".area-dropdown").selectOption("datacenter");

    // Smart match banner should update to reflect Datacenter
    await expect(page.locator(".smart-match-banner")).toContainText("Datacenter");

    // List should show only matching entity for Datacenter
    const entityItems = page.locator(".entity-picker .entity-list .entity-item");
    await expect(entityItems).toHaveCount(1);
    await expect(entityItems.first()).toContainText("Datacenter Server Cam");
  });

  test("Clicking Auto-Assign opens the SmartMatchModal", async ({ page }) => {
    await page.locator(".unassigned-btn").click();

    // Click Auto-Assign button
    await page.locator(".btn-smart-match").click();

    // Verify modal is visible
    const modal = page.locator(".smart-match-modal");
    await expect(modal).toBeVisible();
    await expect(modal).toContainText("Smart Match Room Assignments");
  });
});
