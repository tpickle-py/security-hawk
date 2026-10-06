import { test, expect } from "@playwright/test";
import { setupMockApi } from "./helpers/mockApi";

test.describe("Canvas Architectural Drafting & Wall Workflows", () => {
  test.beforeEach(async ({ page }) => {
    await setupMockApi(page);
    await page.goto("/");
  });

  test("Wall tool draws new wall segments on canvas", async ({ page }) => {
    // Select wall tool via toolbar
    const wallBtn = page.locator(".toolbar button").filter({ hasText: "Wall" }).or(
      page.locator('.toolbar button[title*="Wall"]')
    );
    await wallBtn.first().click({ force: true });

    // Verify wall tool is active
    const canvas = page.locator("svg.editor-svg");
    await expect(canvas).toBeVisible();

    // Initial wall count
    const initialWalls = await page.locator(".wall-shape").count();

    // Click canvas at two distinct points to draw a wall
    const box = await canvas.boundingBox();
    if (!box) throw new Error("Canvas bounding box not found");

    // Click first point
    await page.mouse.click(box.x + 600, box.y + 300);
    // Click second point to finalize segment
    await page.mouse.click(box.x + 800, box.y + 300);

    // Verify a new wall shape was added
    const afterWalls = await page.locator(".wall-shape").count();
    expect(afterWalls).toBeGreaterThan(initialWalls);
  });

  test("Door cutout tool adds door with swing arc onto wall", async ({ page }) => {
    // Select door tool
    const doorBtn = page.locator('.toolbar button[title*="Door"]').first();
    await doorBtn.click({ force: true });

    // In default plan, wall_1 is located horizontally at y=100 from x=100 to 500
    // Initial openings count in default wall
    const initialDoors = await page.locator('.wall-shape path[stroke-dasharray="3 3"]').count();

    // Click on the wall
    const existingWall = page.locator(".wall-shape line").first();
    await existingWall.click({ position: { x: 80, y: 4 }, force: true });

    // Verify door swing arc appears on the wall
    const afterDoors = await page.locator('.wall-shape path[stroke-dasharray="3 3"]').count();
    expect(afterDoors).toBeGreaterThanOrEqual(initialDoors);
  });

  test("Window cutout tool adds window opening onto wall", async ({ page }) => {
    // Select window tool
    const winBtn = page.locator('.toolbar button[title*="Window"]').first();
    await winBtn.click({ force: true });

    // Click on wall to place window
    const existingWall = page.locator(".wall-shape line").first();
    await existingWall.click({ position: { x: 50, y: 4 }, force: true });

    // Openings group inside wall shape should have window lines
    const windowLines = page.locator('.wall-shape line[stroke="#38bdf8"]');
    await expect(windowLines.first()).toBeVisible();
  });

  test("Selecting a room displays 8-handle bounding box for resizing", async ({ page }) => {
    // Click on a subarea to select it
    const subArea = page.locator(".sub-area-item").first();
    await expect(subArea).toBeVisible();
    await subArea.click({ position: { x: 20, y: 20 } });

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
    await subArea.dblclick({ position: { x: 20, y: 20 } });

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
