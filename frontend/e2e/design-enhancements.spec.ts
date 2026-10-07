import { test, expect } from "@playwright/test";
import { setupMockApi } from "./helpers/mockApi";

test.describe("Design Mode Enhancements & New Features E2E", () => {
  test.beforeEach(async ({ page }) => {
    await setupMockApi(page);
    await page.goto("/");
  });

  test("Camera and Motion Sensors render FOV coverage cones and aiming vectors in Design mode", async ({ page }) => {
    const coverageLayer = page.locator(".endpoints-coverage-layer");
    await expect(coverageLayer).toBeVisible();

    const coverageCones = coverageLayer.locator(".editor-coverage-cone");
    // ep_cam_1 (camera) and ep_motion_1 (motion) both have coverage cones rendered
    await expect(coverageCones).toHaveCount(2);

    // Camera coverage cone styling (indigo tint)
    const cameraCone = coverageCones.first();
    const cameraD = await cameraCone.getAttribute("d");
    expect(cameraD).toContain("M 0 0 L");
    expect(cameraD).toContain("A 120 120");

    // Directional aiming vector line and arrow tip exist
    const aimingLines = coverageLayer.locator("line");
    await expect(aimingLines).toHaveCount(2);
    const aimingTips = coverageLayer.locator("polygon");
    await expect(aimingTips).toHaveCount(2);
  });

  test("App version badge is displayed in the header brand section and Settings modal", async ({ page }) => {
    // Top header version badge
    const headerBadge = page.locator(".app-header .app-version-badge");
    await expect(headerBadge).toBeVisible();
    await expect(headerBadge).toHaveText(/v0\.4\.\d+/);

    // Open Settings modal
    const settingsBtn = page.locator(".settings-btn");
    await settingsBtn.click();

    const settingsModal = page.locator(".settings-modal");
    await expect(settingsModal).toBeVisible();

    // Version tag inside settings header
    const settingsVersionTag = settingsModal.locator(".app-version-tag");
    await expect(settingsVersionTag).toBeVisible();
    await expect(settingsVersionTag).toContainText(/0\.4\.\d+/);
  });

  test("Pressing Delete key deletes selected endpoint from canvas", async ({ page }) => {
    const endpoints = page.locator(".endpoint-icon-group");
    const initialCount = await endpoints.count();
    expect(initialCount).toBe(3);

    // Select the first endpoint
    await endpoints.first().click();
    await expect(endpoints.first()).toHaveClass(/selected/);

    // Press Delete key
    await page.keyboard.press("Delete");

    // Endpoint is deleted
    await expect(page.locator(".endpoint-icon-group")).toHaveCount(initialCount - 1);
  });

  test("Pressing Backspace key deletes selected room shape from canvas", async ({ page }) => {
    // Click on room shape to select it
    const room = page.locator(".room-shape").first();
    await room.click({ force: true });

    // Verify 8-handle room-resize-overlay appears
    const resizeOverlay = page.locator(".room-resize-overlay");
    await expect(resizeOverlay).toBeVisible();

    // Press Backspace key
    await page.keyboard.press("Backspace");

    // Room shape is deleted
    await expect(resizeOverlay).not.toBeVisible();
  });

  test("Right-click context menu supports duplicate and properties actions", async ({ page }) => {
    const subarea = page.locator(".sub-area-item").first();
    await expect(subarea).toBeVisible();

    // Right-click subarea to open context menu
    await subarea.click({ button: "right" });

    const contextMenu = page.locator(".context-menu");
    await expect(contextMenu).toBeVisible();
    await expect(contextMenu).toContainText("Duplicate Room");
    await expect(contextMenu).toContainText("Change Style / Color");
    await expect(contextMenu).toContainText("View Properties");

    // Click Duplicate
    const initialSubAreasCount = await page.locator(".sub-area-item").count();
    await contextMenu.locator(".menu-item").filter({ hasText: "Duplicate" }).click();

    // New duplicated subarea exists
    await expect(page.locator(".sub-area-item")).toHaveCount(initialSubAreasCount + 1);
  });
});
