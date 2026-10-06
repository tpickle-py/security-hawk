import { test, expect } from "@playwright/test";
import { setupMockApi } from "./helpers/mockApi";

test.describe("Canvas Architectural Drafting & Wall Workflows", () => {
  test.beforeEach(async ({ page }) => {
    await setupMockApi(page);
    await page.goto("/");
  });

  test("Wall tool draws new wall segments on canvas", async ({ page }) => {
    // Select wall tool via toolbar
    const wallBtn = page.locator('.toolbar button[title*="Draw Wall"]').first();
    await wallBtn.click({ force: true });

    // Verify wall tool is active
    const canvas = page.locator("svg.editor-svg");
    await expect(canvas).toBeVisible();

    // Initial wall count
    const initialWalls = await page.locator(".wall-shape").count();

    // Click canvas at two distinct points to draw a wall (outside the room)
    await canvas.click({ position: { x: 400, y: 600 } });
    await canvas.click({ position: { x: 600, y: 600 } });

    // Verify a new wall shape was added
    const afterWalls = await page.locator(".wall-shape").count();
    expect(afterWalls).toBeGreaterThan(initialWalls);
  });

  test("Door cutout tool adds door with swing arc onto wall", async ({ page }) => {
    // Select door tool
    const doorBtn = page.locator('.toolbar button[title*="Door"]').first();
    await doorBtn.click({ force: true });

    // Initial openings count in default wall
    const initialDoors = await page.locator('.wall-shape path[stroke-dasharray="3 3"]').count();

    // Click on the wall using dispatchEvent to bypass Playwright SVG hit testing flakiness
    const existingWall = page.locator(".wall-shape line").first();
    const box = await existingWall.boundingBox();
    if (box) {
      await existingWall.dispatchEvent("click", {
        clientX: box.x + box.width / 2,
        clientY: box.y + box.height / 2,
      });
    }

    // Verify door swing arc appears on the wall
    await expect(page.locator('.wall-shape path[stroke-dasharray="3 3"]')).toHaveCount(initialDoors + 1);
  });

  test("Window cutout tool adds window opening onto wall", async ({ page }) => {
    // Select window tool
    const winBtn = page.locator('.toolbar button[title*="Window"]').first();
    await winBtn.click({ force: true });

    // Click on wall using dispatchEvent to bypass Playwright SVG hit testing flakiness
    const existingWall = page.locator(".wall-shape line").first();
    const box = await existingWall.boundingBox();
    if (box) {
      await existingWall.dispatchEvent("click", {
        clientX: box.x + box.width / 2,
        clientY: box.y + box.height / 2,
      });
    }

    // Openings group inside wall shape should have window lines
    const windowLines = page.locator('.wall-shape line[stroke="#38bdf8"]');
    await expect(windowLines).toHaveCount(3);
  });

  test("Selecting a room displays 8-handle bounding box for resizing", async ({ page }) => {
    // Click on a subarea to select it
    const subArea = page.locator(".sub-area-item").first();
    await expect(subArea).toBeVisible();
    await subArea.click({ force: true });

    // Bounding box overlay should appear
    const resizeOverlay = page.locator(".room-resize-overlay");
    await expect(resizeOverlay).toBeVisible();

    // 8 resize handles (rect elements with cursor style)
    const handles = resizeOverlay.locator("rect[cursor], rect[style*='cursor']");
    await expect(handles).toHaveCount(8);
  });

  test("Double-clicking room initiates inline rename and updates room title", async ({ page }) => {
    const subArea = page.locator(".sub-area-item").first();
    await expect(subArea).toContainText("Living Room");

    // Double-click to start inline rename
    await subArea.dblclick({ force: true });

    // Inline rename input should appear inside <foreignObject>
    const renameInput = page.locator(".inline-rename-input");
    await expect(renameInput).toBeVisible();
    await expect(renameInput).toHaveValue("Living Room");

    // Fill new name and press Enter to commit
    await renameInput.fill("Primary Control Center");
    await renameInput.press("Enter");

    // Input disappears and room label updates
    await expect(renameInput).not.toBeVisible();
    await expect(subArea).toContainText("Primary Control Center");
  });
});
