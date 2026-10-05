# Home Assistant Add-on: Security Hawk

Interactive multi-floor plan viewer and security monitoring hub for Home Assistant. Features live entity and companion sensor state, low-latency live camera streaming, motion traversal trails, building roll-ups, customizable compound alert rules, an embedded Model Context Protocol (MCP) AI server, an AutoCAD-style command bar, smart keyword matching, magnetic alignment guides, and direct full-screen kiosk mode for wall displays and TVs.

---

## Table of Contents

- [Installation](#installation)
- [Configuration Options](#configuration-options)
- [How to Use](#how-to-use)
  - [1. Ingress (Editor & Control Panel)](#1-ingress-editor--control-panel)
  - [2. Setting Up Floor Plans](#2-setting-up-floor-plans)
  - [3. Workspace Presets (Mapping, CAD, Zen)](#3-workspace-presets-mapping-cad-zen)
  - [4. Live Monitoring Mode](#4-live-monitoring-mode)
  - [5. Direct Kiosk Mode (TVs & Wall Mounts)](#5-direct-kiosk-mode-tvs--wall-mounts)
- [Core Features](#core-features)
  - [Model Context Protocol (MCP) AI Tools Server](#model-context-protocol-mcp-ai-tools-server)
  - [AutoCAD Command Bar & Keyboard-First Navigation](#autocad-command-bar--keyboard-first-navigation)
  - [Smart Match & Keyword Taxonomy Engine](#smart-match--keyword-taxonomy-engine)
  - [Magnetic Smart Guides & Direct Canvas Drop](#magnetic-smart-guides--direct-canvas-drop)
  - [Interactive 8-Handle Room Resizing & Dragging](#interactive-8-handle-room-resizing--dragging)
  - [Dockable & Minimizable Panels](#dockable--minimizable-panels)
  - [Word-Style Room & Subsection Grid Matrix Generator](#word-style-room--subsection-grid-matrix-generator)
  - [Viewport & Device Aspect Ratio Simulators](#viewport--device-aspect-ratio-simulators)
  - [Camera Live Video Streaming & FOV Cones](#camera-live-video-streaming--fov-cones)
  - [Motion Traversal Trails](#motion-traversal-trails)
  - [Site Overview & Building Roll-Up](#site-overview--building-roll-up)
  - [Compound Rules & Notifications](#compound-rules--notifications)
  - [Floor Plan Bundles (.zip Export / Import)](#floor-plan-bundles-zip-export--import)
- [Data Storage & Backups](#data-storage--backups)
- [Support](#support)

---

## Installation

1. Add this repository to your Home Assistant Add-on Store (*Settings &rarr; Add-ons &rarr; Add-on Store &rarr; Repositories*):
   ```txt
   https://github.com/tpickle-py/ha-addons
   ```
2. In the Add-on Store, find and click **Security Hawk**.
3. Click **Install**.
4. (Optional) Toggle **Show in sidebar** for quick one-click navigation.
5. Click **Start**, then click **Open Web UI**.

---

## Configuration Options

Configure options via the **Configuration** tab in the Home Assistant Add-on interface:

| Option | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `kiosk_enabled` | boolean | `false` | Enable the direct unauthenticated web port for smart TVs and wall-mounted kiosks. |
| `kiosk_port` | port | `8100` | Network port for direct kiosk access. Must match your host port mapping. |
| `kiosk_token` | string | `""` | Secret token required in the kiosk URL. If left empty, a secure 32-character token is auto-generated on startup and logged. |
| `default_view` | list | `overview` | Default view when opening Security Hawk: `overview` (3D multi-floor site overview) or `floor` (first floor plan). |
| `quiet_return_seconds` | integer | `120` | Inactivity timer (seconds). Follow-activity mode returns to the overview after this duration of no sensor activity. |

---

## How to Use

### 1. Ingress (Editor & Control Panel)

Security Hawk is fully integrated with Home Assistant Ingress:
- Click **Open Web UI** or select **Security Hawk** from your Home Assistant sidebar.
- Access is protected by your Home Assistant authentication session with zero credential prompts.
- Allows editing plans, placing entities, configuring MCP permissions, managing rules, and adjusting layout settings.

### 2. Setting Up Floor Plans

1. **Background**: Upload an architectural floor plan image (PNG, JPG, SVG, or PDF) or start with a blank canvas.
2. **Drawing Tools**: Draw walls with orthogonal angle lock, room polygons with automatic centroid labeling, cutouts for doors/windows, and text labels.
3. **Scale**: Click the **Scale** tool, click two points on your plan with known distance, and enter real-world meters.
4. **Place Endpoints**:
   - Drag sensors, doors, windows, and cameras directly from the Home Assistant entity picker panel onto the plan.
   - Or drag unassigned entities directly onto a room polygon on the canvas to auto-designate Home Assistant areas instantly.
   - Use **⚡ Auto-Detect Companions** to automatically link low battery, tamper, and temperature sensors.
   - Bind cameras to motion and contact sensors for instant alert popups.
   - Adjust detection range and field-of-view (FOV) cones.

### 3. Workspace Presets (Mapping, CAD, Zen)

Switch between optimized workflows with one click in the top toolbar:
- **🗺️ Mapping Mode**: Dual-column layout with the Home Assistant Entity Picker on the left and Properties on the right.
- **⌨️ CAD Focus**: Collapses side panels into floating status badges and docks the AutoCAD Command Bar at the bottom for keyboard-first drafting.
- **🧘 Zen Canvas**: Minimizes all toolbars and panels into unobtrusive pills, dedicating the entire screen to the floor plan canvas.

### 4. Live Monitoring Mode

Switch from **Design Mode** to **Live Mode** in the toolbar:
- **Motion Sensors**: Animated radar pulse on detection.
- **Doors & Windows**: Architectural 90° swing arcs and open sash status indicators.
- **Cameras**: Windowed live snapshot modal or low-latency MJPEG live stream.
- **Follow-Activity**: Automatically pans and zooms to newly active sensors across floors.
- **TV Remote Navigation**: Full D-pad arrow key and Tab navigation with visible focus rings.

### 5. Direct Kiosk Mode (TVs & Wall Mounts)

Direct Kiosk mode is designed for non-interactive displays, Google TV, Android TV, and wall tablets:

1. In the add-on **Configuration** tab, set `kiosk_enabled: true`.
2. Under the **Network** configuration card, assign host port `8100` (or your preferred port).
3. Click **Save** and restart the add-on.
4. Check the add-on **Log** tab to retrieve your `kiosk_token` (or specify your own in configuration).
5. Open the direct kiosk URL on your display or TV browser:
   ```txt
   http://<YOUR_HA_IP>:8100/kiosk/?token=<YOUR_KIOSK_TOKEN>
   ```

---

## Core Features

### Model Context Protocol (MCP) AI Tools Server

Security Hawk includes a built-in Model Context Protocol (MCP) server allowing AI agents (such as Claude Desktop, Antigravity, or custom LLM orchestrators) to interact with your smart home layout safely:
- **Standard Protocol Endpoints**: Supports JSON-RPC 2.0 (`POST /api/mcp/rpc`) as well as direct REST inspection (`GET /api/mcp/tools`, `POST /api/mcp/execute`, `GET /api/mcp/status`).
- **5 Granular Access Control Tiers**: Configure access in *Settings &rarr; MCP Settings*:
  - `read_only`: Inspect floor plans, query entities, check coverage recommendations.
  - `design_only`: Read access plus creating and updating rooms, sub-areas, and walls.
  - `rules_only`: Read access plus creating and modifying compound rules.
  - `full_access`: Unrestricted access across design and rule creation.
  - `disabled`: Rejects all incoming MCP calls with 403 Forbidden.
- **Sensitive Data Redaction**: Automatic scrubbing of IPv4 addresses (`[REDACTED_IP]`) and authentication headers (`[REDACTED_TOKEN]`).
- **One-Click Security Audits**: Surface blind spots and perimeter gaps using `validate_security_coverage`.

### AutoCAD Command Bar & Keyboard-First Navigation

- **Global `/` or `:` Activation**: Press `/` from anywhere on the canvas to immediately focus the command prompt without touching your mouse.
- **20+ CAD Commands**: Execute `WALL`, `ROOM`, `DOOR`, `WINDOW`, `SELECT`, `PAN`, `ZOOM`, `SCALE`, `SAVE`, `UNDO`, `REDO`, `AUDIT`, `ZEN`, etc.
- **Dynamic Contextual Action Chips**: Action buttons (`[ROTATE 90°]`, `[RENAME]`, `[GRID]`, `[AUDIT]`) automatically adapt based on what you currently have selected on the canvas.
- **Dockable Terminal**: Dock the command bar to the `bottom`, `top`, or let it `float`. Includes an expandable command reference cheat-sheet.

### Smart Match & Keyword Taxonomy Engine

- **Taxonomy Dictionary**: Built-in library mapping common device names and abbreviations (`lr`, `mbr`, `kit`, `wc`, `gar`, `off`, `din`, etc.) across 13 architectural room domains.
- **Fuzzy Confidence Scoring**: Matches unassigned Home Assistant entities to rooms with tokenization and Levenshtein distance metrics.
- **1-Click Batch Review**: Review proposed matches in an interactive modal with confidence badges (`High` vs `Medium`) and apply all designations in a single click.

### Magnetic Smart Guides & Direct Canvas Drop

- **Direct Canvas Drop**: Drag an unassigned entity directly from the panel and drop it into a room on the canvas—Security Hawk automatically designates its Home Assistant area with 0 dropdown clicks.
- **Magnetic Alignment Guides**: When dragging or resizing rooms and walls, cyan dashed alignment guides automatically appear when edges align with nearby structures.
- **Double-Click Inline Renaming**: Double-click any room title or sub-area label to open an inline SVG input (`Enter` to save, `Esc` to cancel).

### Interactive 8-Handle Room Resizing & Dragging

- Select any architectural room or sub-area to reveal an interactive 8-handle bounding box (`NW`, `N`, `NE`, `E`, `SE`, `S`, `SW`, `W`).
- Drag any corner or edge to dynamically reshape and scale rooms with live dimension badges (`W × H px`).

### Dockable & Minimizable Panels

- The **Entity Picker** and **Properties** panels can be docked to the `left`, `right`, or set to free-floating (`float`).
- Drag panels freely across the viewport via their grab handles; coordinates are automatically remembered in `localStorage`.
- Minimize panels into unobtrusive floating pill badges (`🏷️ Entities (N)`, `📐 Properties & Zones`) to maximize canvas workspace.

### Word-Style Room & Subsection Grid Matrix Generator

- Hover over an 8×8 matrix grid in the toolbar (just like inserting a table in Microsoft Word) to generate multi-room layouts instantly.
- Subdivide existing rooms into closets, pantries, or storage zones with live SVG previews, custom room naming prefixes, and optional interior dividing walls and doors.

### Viewport & Device Aspect Ratio Simulators

- Preview floor plans accurately across standard physical displays: Phone Portrait (9:16), Phone Landscape (16:9), Wall Tablet (4:3 / 16:10), TV (16:9), and Ultrawide (21:9).
- Visual safe-area letterboxing and one-click **Fit View** to ensure your layout displays perfectly on wall kiosks.

### Camera Live Video Streaming & FOV Cones

- **Live Streaming**: Low-latency MJPEG proxy streaming directly from Home Assistant Core (`/camera_proxy_stream/{entity_id}`) into the linked camera popup window, with automatic snapshot fallback.
- **Camera FOV Cones**: Interactive beam angle (15°–180°) and depth sliders rendering live field-of-view cones on the canvas, complete with 90° forward-aligned camera icons and dashed aiming vectors.

### Motion Traversal Trails

- When multiple sensors trigger sequentially, Security Hawk correlates activations within a sliding 45-second window.
- Renders an animated flowing gradient trail (`#818cf8` &rarr; `#06b6d4` &rarr; `#f59e0b`) with numbered checkpoint sequence badges (`#1`, `#2`, `#3`) and elapsed timers (`+0s`, `+5s`, `+14s`) to visualize intruder path of travel.

### Site Overview & Building Roll-Up

- Monitor multi-story homes or detached outbuildings simultaneously.
- A floating HUD summarizes open doors/windows, active motion detections, and offline entities across structures with 1-click drill-down into specific floors.

### Compound Rules & Notifications

- Multi-condition trigger engine supporting `ALL` (AND) and `ANY` (OR) logic with time-window correlation (e.g. motion detected within 30s of door opening).
- Automated dispatch via pluggable notification backends: Home Assistant Services, SMTP Email, WhatsApp (CallMeBot / Twilio), Discord webhooks, Slack, Telegram bot, or custom HTTP webhooks.
- Decoupled asynchronous background worker (`RuleEventWorker`) preventing alert actions from lagging the main event loop.

### Floor Plan Bundles (.zip Export / Import)

- Export entire floor plans, custom images, assets, and rules into a single portable `.zip` bundle for easy backup or transfer.
- Universal import engine with ZipSlip path traversal protection and automatic schema migrations.

---

## Data Storage & Backups

- Plans, uploaded blueprints, asset images, and version history are stored inside `/data/` in the container.
- The `/data` volume is automatically included in standard Home Assistant backups (Supervisor backups).
- Security Hawk maintains the last 20 rolling versions of each floor plan for rollback safety.

---

## Support

- [GitHub Repository](https://github.com/tpickle-py/security-hawk)
- [Issue Tracker](https://github.com/tpickle-py/security-hawk/issues)
- [Add-on Catalog](https://github.com/tpickle-py/ha-addons)
