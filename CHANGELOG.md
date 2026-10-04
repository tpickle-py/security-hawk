# Changelog

All notable changes to Security Hawk will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.10] - 2026-10-04

### Changed
Add Kiosk share links in Settings, active viewer telemetry, and bulk hide for entity types

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

### Changed
- Fix s6-overlay container supervision conflicts in Home Assistant by setting init: false
- Add hassio_api: true and hassio_role: default for Supervisor API token injection
- Safe fallback defaults in run.sh and settings.py for KIOSK_PORT, QUIET_RETURN_SECONDS, and SUPERVISOR_TOKEN
- Fix async event loop handling in synchronous camera snapshot fallback view
- Automated semantic version release script (scripts/bump_version.py)

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
