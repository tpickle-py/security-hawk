import { test, expect } from "@playwright/test";
import { setupMockApi } from "./helpers/mockApi";

test.describe("Command Bar E2E Workflows", () => {
  test.beforeEach(async ({ page }) => {
    await setupMockApi(page);
    await page.goto("/");
  });

  test("Command Bar opens via keyboard shortcut '/' and focuses prompt input", async ({ page }) => {
    // Press '/' on the body
    await page.keyboard.press("/");

    const cadBar = page.locator(".cad-command-bar");
    await expect(cadBar).toBeVisible();

    const input = page.locator(".cad-input");
    await expect(input).toBeFocused();
    await expect(page.locator(".cad-title")).toContainText("Command Bar");
  });

  test("Command Bar toggles via toolbar button", async ({ page }) => {
    // Toolbar button with text Command Bar or icon ⌨️
    const cadToggle = page.locator(".toolbar button").filter({ hasText: "Command Bar" });
    await expect(cadToggle).toBeVisible();

    // Command bar is open by default, toggle off
    await cadToggle.click({ force: true });
    await expect(page.locator(".cad-command-bar")).not.toBeVisible();

    // Toggle back on
    await cadToggle.click({ force: true });
    await expect(page.locator(".cad-command-bar")).toBeVisible();
  });

  test("Executing 'WALL' command changes active tool to wall", async ({ page }) => {
    await page.keyboard.press("/");
    const input = page.locator(".cad-input");
    await input.fill("WALL");
    await page.keyboard.press("Enter");

    // Terminal log contains tool activation
    await expect(page.locator(".cad-log-line.output").last()).toContainText("Wall tool activated");

    // Header badge reflects tool
    await expect(page.locator(".cad-active-tool")).toContainText("WALL");
  });

  test("Executing 'ROOM' command changes active tool to room", async ({ page }) => {
    await page.keyboard.press("/");
    const input = page.locator(".cad-input");
    await input.fill("ROOM");
    await page.keyboard.press("Enter");

    await expect(page.locator(".cad-log-line.output").last()).toContainText("Room polygon tool activated");
    await expect(page.locator(".cad-active-tool")).toContainText("ROOM");
  });

  test("Executing 'ZOOM IN' and 'ZOOM OUT' modifies zoom levels", async ({ page }) => {
    await page.keyboard.press("/");
    const input = page.locator(".cad-input");

    await input.fill("ZOOM IN");
    await page.keyboard.press("Enter");
    await expect(page.locator(".cad-log-line.output").last()).toContainText("Zoomed in");

    await input.fill("ZOOM OUT");
    await page.keyboard.press("Enter");
    await expect(page.locator(".cad-log-line.output").last()).toContainText("Zoomed out");
  });

  test("Executing 'ZEN' activates Zen mode and minimizes side panels", async ({ page }) => {
    await page.keyboard.press("/");
    const input = page.locator(".cad-input");
    await input.fill("ZEN");
    await page.keyboard.press("Enter");

    // In Zen mode, panels are minimized to floating pills
    await expect(page.locator(".entity-minimized-pill").filter({ hasText: "Entities" })).toBeVisible();
  });

  test("Cycling dock positions updates CAD bar classes (bottom, top, float)", async ({ page }) => {
    await page.keyboard.press("/");
    const cadBar = page.locator(".cad-command-bar");
    const dockBtn = page.locator(".cad-header .cad-btn").filter({ hasText: "⚓" });

    // Initial dock is bottom
    await expect(cadBar).toHaveClass(/dock-bottom/);

    // Cycle to top
    await dockBtn.click();
    await expect(cadBar).toHaveClass(/dock-top/);

    // Cycle to float
    await dockBtn.click();
    await expect(cadBar).toHaveClass(/dock-float/);

    // Cycle back to bottom
    await dockBtn.click();
    await expect(cadBar).toHaveClass(/dock-bottom/);
  });

  test("Command history navigation recalls past commands with ArrowUp and ArrowDown", async ({ page }) => {
    await page.keyboard.press("/");
    const input = page.locator(".cad-input");

    await input.fill("WALL");
    await page.keyboard.press("Enter");

    await input.fill("DOOR");
    await page.keyboard.press("Enter");

    // ArrowUp recalls DOOR
    await page.keyboard.press("ArrowUp");
    await expect(input).toHaveValue("DOOR");

    // ArrowUp again recalls WALL
    await page.keyboard.press("ArrowUp");
    await expect(input).toHaveValue("WALL");

    // ArrowDown goes back to DOOR
    await page.keyboard.press("ArrowDown");
    await expect(input).toHaveValue("DOOR");
  });

  test("Autocomplete dropdown shows matching commands and completes input", async ({ page }) => {
    await page.keyboard.press("/");
    const input = page.locator(".cad-input");

    await input.fill("RO");
    const autocomplete = page.locator(".cad-autocomplete");
    await expect(autocomplete).toBeVisible();

    // Suggestions should include ROOM or ROTATE
    const suggestion = page.locator(".suggestion-item .sugg-cmd").filter({ hasText: "ROOM" });
    await expect(suggestion).toBeVisible();

    await suggestion.click();
    // Prompt line should execute ROOM
    await expect(page.locator(".cad-active-tool")).toContainText("ROOM");
  });

  test("Helper drawer opens with 'HELP' command and displays reference guide", async ({ page }) => {
    await page.keyboard.press("/");
    const input = page.locator(".cad-input");

    await input.fill("HELP");
    await page.keyboard.press("Enter");

    const helper = page.locator(".cad-helper-drawer");
    await expect(helper).toBeVisible();
    await expect(helper).toContainText("Command Reference");
    await expect(helper).toContainText("Draw Commands");

    // Close helper
    await page.locator(".helper-close-btn").click();
    await expect(helper).not.toBeVisible();
  });
});
