import { test, expect } from "@playwright/test";
import { setupMockApi } from "./helpers/mockApi";

test.describe("Workspace Presets, Panel Docking & Security Audit E2E", () => {
  test.beforeEach(async ({ page }) => {
    page.on("console", (msg) => console.log("E2E_CONSOLE:", msg.text()));
    await setupMockApi(page);
    await page.goto("/");
  });

  test("Minimizing and expanding the EntityPicker panel", async ({ page }) => {
    const entityPicker = page.locator(".entity-picker");
    await expect(entityPicker).toBeVisible();

    // Click minimize button (─) in entity picker header
    const minBtn = entityPicker.locator('button[title*="Minimize"]').or(
      entityPicker.locator(".panel-tool-btn").filter({ hasText: "─" })
    );
    await minBtn.click({ force: true });

    // EntityPicker panel collapses
    await expect(entityPicker).not.toBeVisible();

    // Minimized floating pill appears
    const pill = page.locator(".entity-minimized-pill");
    await expect(pill).toBeVisible();
    await expect(pill).toContainText("Entities");

    // Click the pill to restore
    await pill.click({ force: true });
    await expect(entityPicker).toBeVisible();
  });

  test("Workspace presets toggle between Mapping, CAD, and Zen layouts", async ({ page }) => {
    // 1. Switch to CAD mode
    const cadPreset = page.locator(".preset-btn[title*='CAD']");
    await cadPreset.click();
    await expect(page.locator(".cad-command-bar")).toBeVisible();

    // 2. Switch to Zen mode
    const zenPreset = page.locator(".preset-btn[title*='Zen']");
    await zenPreset.click({ force: true });
    // Panels should be minimized
    await expect(page.locator(".entity-minimized-pill")).toBeVisible();
    await expect(page.locator(".cad-command-bar")).not.toBeVisible();

    // 3. Switch back to Mapping mode
    const mapPreset = page.locator(".preset-btn[title*='Mapping']");
    await mapPreset.click({ force: true });
    await expect(page.locator(".entity-picker")).toBeVisible();
  });

  test("AI Security Coverage Audit modal fetches recommendations and displays stats HUD", async ({ page }) => {
    // Click Audit button in toolbar
    const auditBtn = page.locator(".toolbar button.audit-btn");
    await expect(auditBtn).toBeVisible();
    await auditBtn.click({ force: true });

    // Coverage Audit modal opens
    const auditModal = page.locator(".audit-modal");
    await expect(auditModal).toBeVisible();
    await expect(auditModal).toContainText("Security Coverage & Gap Audit");

    // Status banner shows coverage gaps identified
    await expect(page.locator(".status-banner")).toContainText("Coverage Gaps Identified");

    // Stats grid renders correct counts from mockApi
    const statsGrid = page.locator(".stats-grid");
    await expect(statsGrid).toContainText("Rooms");
    await expect(statsGrid).toContainText("Zones");
    await expect(statsGrid).toContainText("Sensors");

    // Recommendations list contains AI recommendations
    const recList = page.locator(".rec-list");
    await expect(recList).toContainText("rear patio doorway");
    await expect(recList).toContainText("10m dead zone");

    // Close button dismisses modal
    await page.locator(".audit-modal .btn-done").click();
    await expect(auditModal).not.toBeVisible();
  });

  test("Screen aspect simulator previews different aspect ratios", async ({ page }) => {
    // Open viewport presets menu
    const aspectBtn = page.locator(".viewport-btn");
    await expect(aspectBtn).toBeVisible();
    await aspectBtn.click();

    const menu = page.locator(".viewport-menu");
    await expect(menu).toBeVisible();
    await expect(menu).toContainText("Preview Screen Aspect");

    // Select Phone Portrait
    const phoneOption = page.locator(".viewport-menu-item").filter({ hasText: "Phone (Portrait" });
    await phoneOption.click();

    // Viewport button label updates
    await expect(aspectBtn).toContainText("9:16");

    // Viewport guide layer is rendered on canvas
    const viewportGuide = page.locator(".viewport-guide-layer");
    await expect(viewportGuide).toBeVisible();
  });
});
