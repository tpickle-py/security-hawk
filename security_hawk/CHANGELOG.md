# Changelog

All notable changes to Security Hawk will be documented in this file.

## [0.4.2] - 2026-10-06

### Changed
Fix e2e test suite for canvas drawing tools and svg interactivity

## [0.4.1] - 2026-10-05

### Added
- **Playwright E2E Test Suite & CI Automation**:
  - Comprehensive end-to-end test coverage across Entity Picker, Command Bar, Canvas drawing, Wall and opening cutouts, Endpoint grouping, Workspace presets, and Security Audit modal.
  - Complete mock API backend fixtures (`frontend/e2e/helpers/mockApi.ts`) for fast, hermetic test runs.
  - Automated GitHub Actions E2E workflow (`.github/workflows/e2e.yaml`) with Playwright HTML artifact archiving.
- **Command Bar Grouping & Ungrouping**:
  - Dedicated `GROUP` and `UNGROUP` commands and dynamic quick-action chips for multi-selected endpoints.

### Changed
- **Home Assistant Sidebar Icon**:
  - Configured `panel_icon: "mdi:shield-eye"` in add-on manifest for a sleek Home Assistant sidebar icon.
- **Command Bar Clean Branding**:
  - Standardized all terminology to "Command Bar" across UI, hotkeys, tooltips, and documentation.
- **Entity Picker & Smart Match Enhancements**:
  - Smart Match now respects active area and domain filter selections, allowing targeted batch assignments.
  - Resolved list item overlap issues and sticky scroll states in the entity drawer.
  - Reactive unassigned count badge updating immediately on filter or area changes.
- **Canvas Ergonomics & Layout Fixes**:
  - Added transparent SVG hitbox targets and FOV cone pointer isolation for reliable endpoint drag selection.
  - Constrained toolbar overflow and adjusted z-indexing to prevent canvas control clipping on smaller viewports.

## [0.4.0] - 2026-10-05

### Added
- **Model Context Protocol (MCP) AI Tools Server**:
  - Embedded Model Context Protocol server exposing JSON-RPC 2.0 (`POST /api/mcp/rpc`) and direct REST endpoints (`GET /api/mcp/tools`, `POST /api/mcp/execute`, `GET /api/mcp/status`).
  - 5 configurable access control permission tiers (`read_only`, `design_only`, `rules_only`, `full_access`, `disabled`) with optional Bearer / X-MCP-Key token authentication.
  - Automatic sensitive data redaction masking IPv4 addresses (`[REDACTED_IP]`) and authentication headers (`[REDACTED_TOKEN]`).
  - Native tools for AI assistants to inspect layouts, audit security coverage gaps, construct rooms/walls, and synthesize compound rules.
- **Command Bar & Keyboard Ergonomics**:
  - Keyboard-first command terminal supporting 20+ CAD commands (`WALL`, `ROOM`, `DOOR`, `WINDOW`, `SELECT`, `PAN`, `ZOOM`, `SCALE`, `SAVE`, `UNDO`, `REDO`, `AUDIT`, `ZEN`).
  - Global `/` or `:` hotkey activation focusing the command line from anywhere on the canvas.
  - Contextual quick-action chips (`[ROTATE 90°]`, `[RENAME]`, `[GRID]`, `[AUDIT]`) that dynamically adapt to the currently selected object.
  - Collapsible quick-reference drawer and dockable placement (`bottom`, `top`, `float`).
- **Keyword Taxonomy & "Smart Match" 1-Click Engine**:
  - Comprehensive keyword taxonomy library covering 13 architectural room types with tokenization and abbreviation expansion (`lr`, `mbr`, `kit`, `wc`, `gar`, `off`, `din`, etc.).
  - Confidence scoring engine combining exact token matching with fuzzy Levenshtein distance metrics.
  - Interactive Smart Match review modal with confidence badges (`High` vs `Medium`), match rationales, and 1-click batch area assignment.
  - Point-in-polygon canvas drop hit-testing: dragging an unassigned entity card directly onto any room polygon automatically designates its Home Assistant area with 0 dropdown clicks.
- **Magnetic Smart Alignment Guides & Inline Renaming**:
  - Dynamic edge snapping displaying cyan dashed alignment lines when moving or resizing rooms and sub-areas.
  - Double-click inline room and sub-area title editing via embedded SVG `<foreignObject>` (`Enter` to save, `Esc` to cancel).
- **Dockable & Minimizable Panels**:
  - Entity Picker and Properties panels dockable to `left`, `right`, or free `float` with draggable header bars and persistent `localStorage` coordinates.
  - Minimizable into interactive floating badges (`🏷️ Entities (N)`, `📐 Properties & Zones`) to maximize drafting space.
- **Interactive 8-Handle Room Resizing & Dragging**:
  - Direct dragging of rooms and sub-areas across canvas space.
  - Interactive 8-handle bounding box (`NW`, `N`, `NE`, `E`, `SE`, `S`, `SW`, `W`) recalculating vertices dynamically during drag operations.
- **Workspace Presets & Zen Canvas**:
  - 1-click layout switcher in Toolbar between `🗺️ Mapping Mode` (dual-column), `⌨️ CAD Focus` (command bar active, side panels collapsed), and `🧘 Zen Canvas` (maximized drafting canvas).
- **Security Coverage Audit HUD**:
  - One-click `🛡️ Audit` button in toolbar and CAD bar executing MCP `validate_security_coverage` with visual status banners, stats grid, and security gap recommendations.
- **Right-Click Context Menu Modal Popup**:
  - Viewport-clamped context menu for quick actions on canvas, endpoints, rooms, and walls (Properties, Rotate ±90°, Duplicate, Cutout, Room Grid Insert, Delete).
- **Camera 90° FOV Cone Alignment**:
  - Re-aligned camera icon body 90 degrees forward to face the sensor coverage cone and aiming ray.

### Changed
- **Accurate Unassigned & Hidden Entity Counts**: Real-time synchronization of `unassigned_entities_count` reflecting ignored/hidden entities and domain filters without page refresh.

## [0.3.12] - 2026-10-04

### Added
- **Dockable Live Activity Feed & Navigation HUD**: Separated the Live Activity Feed (now defaulting to Bottom Left) and the TV & Touch Navigation Controls HUD (Bottom Right) to eliminate bottom-right menu collisions. Added on-screen quick dock buttons (⚓) to cycle either overlay through all four screen corners (`bottom-left`, `bottom-right`, `top-right`, `top-left`) on the fly.
- **Dockable Editor Toolbar**: Added support for docking the main Design mode drawing toolbar across four distinct orientations (`top` horizontal center, `bottom` horizontal center, `left` vertical sidebar, and `right` vertical sidebar) with smooth animation transitions and an on-toolbar quick dock cycler button.
- **Docked Menus & Overlays Layout in Settings**: Added a new configuration card under *Settings &rarr; Behaviors* allowing users to assign dock corners for the Activity Feed, Navigation HUD, and Toolbar. Includes an automatic collision warning badge when menus share the same corner.
- **Reset Docked Positions**: Added a one-click "↺ Reset Docked Positions" button in Settings that instantly restores all menus and toolbars to their clean, non-overlapping default positions.

## [0.3.11] - 2026-10-04

### Added
- **Word-Style Room & Subsection Grid Overlay Generator**: Added an interactive 8×8 hoverable table matrix picker in the editor toolbar (like inserting a table in Microsoft Word) to instantly generate layouts of rooms or subdivide existing spaces into subsections (e.g. closets, pantries, storage zones). Includes live interactive SVG preview, preset templates (Quad Rooms, Closets/Storage, Suites, Dual Zones), naming prefix customization, and optional interior dividing walls and door openings.
- **Viewport & Device Aspect Ratio Simulators**: Preview floor plans across common real-world display profiles (Phone Portrait 9:16, Phone Landscape 16:9, Wall Tablet 4:3 / 16:10, Living Room TV 16:9, and Ultrawide 21:9) with safe-area letterboxing, aspect badges, and one-click Fit-to-Screen controls.
- **Live View & Kiosk TV / Touch Navigation HUD**: Added direct left-click & touch panning, two-finger pinch-to-zoom for mobile/tablets, an on-screen D-pad navigation cluster (▲, ▼, ◀, ▶, +, −, 🎯, ⛶), a position lock toggle (🔒) to pin wall displays in place, and TV remote/keyboard shortcut support (Arrow keys, Home, L, F).
- **Item Centering & Viewport Fit**: Added a one-click Recenter tool in the editor toolbar that aligns selected endpoints or all floor plan items to the center of the plan bounding box.

### Fixed
- **Multi-Item Drag**: Fixed an issue where dragging multiple selected endpoints would collapse the selection or fail to move all endpoints together; now smoothly translates all selected items in real time with a single undo history snapshot.

## [0.3.10] - 2026-10-04

### Added
- **Kiosk Share Links in Settings**: Added copyable direct Kiosk URLs in Settings with auto-generated security tokens.
- **Active Viewer Telemetry**: Real-time connected viewer counts and active session monitoring.
- **Bulk Hide for Entity Types**: One-click domain bulk-hiding (`switch.*`, `light.*`, `sensor.*`) to filter non-security entities from unassigned lists.

## [0.3.9] - 2026-10-04

### Added
- **Camera Point of View & Depth of View in Editor**: Render live Field of View (FOV) cones directly on the canvas in Design mode, featuring a dashed aiming ray and directional arrowhead indicating aim and rotation angle. Increased depth slider range up to 500px in the properties panel.
- **Entity Hide / Ignore in Entity Picker**: Added a one-click "Hide" button on entity cards so irrelevant entities (diagnostics, non-security smart devices) can be hidden. Added a dedicated "Hidden" tab with count badge to review and unhide entities, with state persisted across sessions.
- **Window vs. Door Sensor Detection**: Added distinct entity classification and icons for windows (🪟) vs. doors (🚪) with support for contact sensors (e.g. Sonoff SNZB-04, Aqara). Added category filter chips (`All`, `Cameras`, `Motion`, `Doors`, `Windows`) to the entity picker.
- **Editable Entity ID**: Allowed direct editing of the Entity ID field in the Property Panel so typos and renamed entities can be fixed without deleting and recreating endpoints.

### Fixed
- **False "Entity Not Found in HA" Warning**: Added `/api/entities/ids/` endpoint to load all registered Home Assistant entity IDs into the frontend store and cross-reference active WebSocket states, preventing valid placed entities outside the initial search window from being falsely flagged as missing.

## [0.3.8] - 2026-10-04

### Fixed
- **Frontend Assets 404**: Configure `asset_view` in `urls.py` to serve Vite JS/CSS/font bundles from `static/frontend/assets` before checking user-uploaded plan assets.
- **WebSocket Reconnect Tight-Loop**: Ensure `HAWebSocketClient._running` is `True` and run `_connect_loop()` in the background listener thread with backoff delays, preventing rapid reconnect loops and redundant registry refreshes.

## [0.3.7] - 2026-10-04

### Changed
- **Multi-Arch Docker Build Performance**: Set `FROM --platform=$BUILDPLATFORM node:20-alpine AS frontend-build` in `Dockerfile` so frontend assets bundle natively on the runner's architecture, speeding up `aarch64` container builds from ~12 minutes down to ~1 minute.

## [0.3.6] - 2026-10-04

### Fixed
- **Supervisor Role & Auth API**: Set `hassio_role: homeassistant` and `auth_api: true` in `config.yaml` to ensure the injected `SUPERVISOR_TOKEN` has proper API authorization scopes.
- **s6-overlay Environment with `with-contenv`**: Set `run.sh` shebang to `#!/usr/bin/with-contenv bashio` so container environment variables (`SUPERVISOR_TOKEN`) are automatically loaded into all child processes.

## [0.3.5] - 2026-10-04

### Fixed
- **Ingress 403 Forbidden**: Support `X-Ingress-Path` and local subnets in `IngressMiddleware` when client IP headers (`X-Forwarded-For`) are forwarded by Daphne.
- **Supervisor API & Token Handling**: Automatically import environment variables saved by `s6-overlay` in `/var/run/s6/container_environment/` so `SUPERVISOR_TOKEN` is available to `bashio` and the Django background listener.
- **Direct Options Loading**: Read `/data/options.json` directly with `jq` in `run.sh` to avoid redundant Supervisor API roundtrips during container boot.

## [0.3.4] - 2026-10-04

### Fixed
- **s6-overlay Supervision**: Prevent container supervision conflicts in Home Assistant by configuring `init: false`.
- **Supervisor Token Access**: Configure `hassio_api: true` and `hassio_role: default` for Supervisor API token injection.
- **Safe Fallback Defaults**: Safe defaults in `run.sh` and `settings.py` for `KIOSK_PORT`, `QUIET_RETURN_SECONDS`, and `SUPERVISOR_TOKEN`.
- **Camera Fallback View**: Fix async event loop handling in synchronous camera snapshot fallback view.
- **Release Automation**: Added automated semantic version release workflow script (`scripts/bump_version.py`).

## [0.3.3] - 2026-10-04

### Fixed
- Add `hassio_api: true` and `hassio_role: default` to grant Supervisor API access for option retrieval and `SUPERVISOR_TOKEN` injection.
- Safeguard `SUPERVISOR_TOKEN` in `run.sh` with default expansion to prevent bash `set -u` unbound variable exits.

## [0.3.2] - 2026-10-03

### Fixed
- Add `init: false` to add-on configuration preventing s6-overlay PID 1 supervision conflicts in Home Assistant.
- Automated release build and cross-repository dispatch workflow for Home Assistant Add-ons repository.

## [0.3.0] - 2026-10-03

### Added
- **Compound Rule Engine ("If X, Y, Z Then Do X")**: Complex multi-condition trigger engine supporting `ALL` (AND) and `ANY` (OR) logic, time-window event correlation (e.g. within 30s), auto-reset countdown timers back to `off`, and linked camera auto-popups.
- **Expandable Action Plugins Architecture**: Pluggable action framework allowing rules to trigger multiple actions simultaneously with dynamic UI schema rendering:
  - **Home Assistant Service (`ha_service`)**: Call native HA services (`alarm_control_panel.alarm_trigger`, `notify`, `light.turn_on`, sirens).
  - **Email Notification (`email`)**: Send formatted SMTP alert emails with variable interpolation (`{rule_name}`, `{entities}`) and TLS encryption.
  - **WhatsApp Messages (`whatsapp`)**: Dispatch instant WhatsApp alerts via CallMeBot (free for HA), Twilio API, or custom webhook gateways.
  - **Discord Alerts (`discord`)**: Dispatch rich color-coded incident cards and embeds to Discord server channels via incoming webhooks.
  - **Slack Notifications (`slack`)**: Post Block Kit formatted alert notifications directly to Slack channels via incoming webhooks.
  - **Telegram Bot Notifications (`telegram`)**: Send real-time instant alerts directly to Telegram users, groups, or channels via Telegram Bot API `sendMessage`.
  - **Custom Webhook / HTTP (`webhook`)**: Send HTTP POST/GET requests with custom JSON payloads and headers to external endpoints or automation servers.
  - **Global Notification Defaults**: Settings page tab for global SMTP and WhatsApp credentials, automatically inherited by rules.
- **Decoupled Background Rule Worker & Event Queue**: Dedicated asynchronous background consumer (`RuleEventWorker`) with `asyncio.Queue` decoupling rule matching, time-window evaluation, and external network actions completely from the main Home Assistant WebSocket pump and frontend broadcasts. Includes runtime telemetry endpoint `GET /api/rules/worker-status/`.
- **MQTT Information Store & Home Assistant MQTT Discovery**: Lightweight zero-dependency async MQTT 3.1.1 client that publishes state changes and automatic Home Assistant MQTT Discovery payloads (`homeassistant/binary_sensor/security_hawk_<rule_id>/config`) with retain support and authentication.
- **Application & Integration Settings**: Dedicated Settings modal to configure automation behaviors (Quiet Return timeout, Camera Snapshot dismiss timeout, default startup view), MQTT broker parameters, and one-click Home Assistant synthetic helper registration.
- **Canvas Synthetic / Composite Endpoints**: Rules and synthetic sensors can now be browsed, tested, and dragged directly from the "⚡ Rules" tab in EntityPicker onto the floor plan canvas as interactive `composite` endpoints with pulsing alert rings.
- **Endpoint Properties & Companion Auto-Discovery**:
  - One-click **"⚡ Auto-Detect Companions"** matching template sensor patterns (`_battery`, `_caution`, `_problem`, `_low_battery`, `_tamper`, `_temperature`).
  - **Linked Cameras Picker**: Direct binding of camera feeds to sensors for automatic live popups on detection.
  - **Stale RF Threshold Selector**: Configurable quiet duration (`1h`, `6h`, `12h`, `24h`, `3d`, `7d`, `30d`) before flagging battery sensors.
  - **Interactive Coverage FOV Controls**: Detection range (px/meters) and beam angle (15°–180°) sliders with real-time canvas preview.
- **Site Overview Building State Roll-Up (Spec §Views)**:
  - Floating overview HUD and canvas markers summarizing structure health across all floors: door/window openings, active motion detections, and sensor totals.
  - Interactive 1-click inspection jumping straight into any structure's active floor plan.
- **Spatio-Temporal Motion Traversal Trails & Correlation**:
  - Live breadcrumb engine correlating sequential sensor activations within a sliding window (45s) to reveal occupant movement from one end of the site to the other.
  - Animated SVG flowing gradient trail (`#818cf8` -> `#06b6d4` -> `#f59e0b`) connecting triggered endpoints.
  - Numbered checkpoint sequence badges (`#1`, `#2`, `#3`) with elapsed duration badges (`+0s`, `+5s`, `+14s`).
  - Occupant lead pulse radar animation tracking current front-line movement.
  - Live toolbar controls with toggle button (`〰️ Motion Trails`) and manual trail clearing.
- **Live Video Streaming Mode**:
  - MJPEG real-time video stream proxying directly from Home Assistant Core (`/camera_proxy_stream/{entity_id}`) into the linked camera popup window (`/api/camera/<entity_id>/stream/`).
  - Modal toggle switch between `📸 Snapshot (2.5s)` and `🔴 Live Video Stream` mode with automatic fallback.
- **Floor Plan Bundle (.zip) Export & Import (Spec §Import and export)**:
  - Complete portable archive packaging containing `plan.json` along with all custom floor plan background blueprint images under `assets/`.
  - Export warning notice dialog notifying users of physical security implications: *"A shared plan bundle contains the layout of a building and where its sensors are. Share with caution."*
  - Smart universal import engine supporting both `.json` and `.zip` archives with automatic ZipSlip path traversal protection and asset directory restoration.

## [0.2.0] - 2026-10-03

### Added
- **Architectural Vector Drawing Tools**: In-editor vector drawing tools with grid and vertex snapping (14px magnetic threshold), wall drawing with orthogonal angle lock, room polygon tool with auto-closing and centroid labeling, and architectural text labels.
- **Wall Cutouts for Doors & Windows**: Click-to-cut openings on existing walls rendering architectural 90° door swings and dual-pane window frame cutouts.
- **Canvas Undo & Redo History**: In-memory 40-step action history with `Ctrl+Z` and `Ctrl+Y` / `Ctrl+Shift+Z` keyboard shortcuts and dedicated toolbar controls.
- **Rolling Version History**: Automated 20-version rolling snapshot modal allowing instant one-click rollback to prior floor plan versions with pre-rollback safety snapshots.
- **Floor Plan JSON Export & Import**: Direct file export (`/api/plans/<id>/export/`) and import (`/api/plans/import/` or `/api/plans/<id>/import/`) for local offline backups, templating, and staging tests.
- **Automated Schema Migrations**: Robust versioned plan migration engine (`schema_version: 1 -> 2`) executing automatically during plan loading, saving, and importing to ensure backwards compatibility with nested shapes, sub-areas, and entity grouping.
- **Linked Camera Auto-Popup**: Automatic windowed camera snapshot popup when linked sensors trigger, featuring a 30-second visual auto-dismiss countdown bar with pause-on-hover and instant `Escape`/`Back` remote dismissal.
- **Live Activity Event Feed**: Collapsible slide-out timeline drawer showing the last 50 state transitions with domain badges, search filtering, and one-click smooth panning/zooming to the target endpoint.
- **Follow-Activity Mode**: Hands-free live tracking mode that automatically centers and highlights active sensors on canvas, with a 120-second quiet-return timer returning to the overview floor plan.
- **Sensor Coverage Cones**: SVG field-of-view (FOV) sector visualization for camera lenses (70° cone) and motion PIR detection zones (85° sector).
- **Stale RF Sensor Flagging**: Automatic warning indicator badges for battery-operated RF sensors that have not reported state updates within configured `stale_after` intervals.

## [0.1.0] - 2026-10-03

### Added
- **Nested Areas (Areas within Areas)**: Sub-area schema and UI to define and render nested room zones (e.g., closet within bedroom) with dashed boundaries and labels.
- **Nested Entities (Entities within Entities)**: Support for attaching child endpoints (multi-sensors, vibration sensors) directly to parent endpoints (doors, cameras) with visual indicator pips.
- **Duplicate Placements**: Allow placing the same Home Assistant entity at more than one spot on the canvas with concurrent real-time WebSocket state synchronization.
- **Door & Window Visual Distinction**: Dedicated architectural symbols showing clear open vs. closed states (door with 90° dotted swing arc; window with slid-open sash and airflow indicator) with alert warning glow.
- **Grouping into Units**: Group multiple endpoints into a unified named unit with canvas `G` unit badges.
- **Marquee Selection & Multi-Move**: Drag on canvas to marquee-select multiple endpoints with Shift modifier, and drag any selected item to move all items simultaneously.
- **TV Remote & Keyboard Navigation**: Full D-pad arrow key navigation jumping to nearest physical endpoints, glowing focus rings, and windowed camera live snapshot modal with `Escape` / remote `Back` dismissal.
- **Home Assistant App & Ingress**: Full Home Assistant add-on architecture with Ingress support, Supervisor event bridge, and area/entity registry caching.
- **Route B Kiosk Mode**: Full-screen, read-only unattended TV display with token authentication and auto-reconnect.
- **Modern uv & Toolchain**: Configured with Astral `uv` (`uv sync`), `ruff` linter/formatter, and `pytest-cov` test suite (23 passing tests).
