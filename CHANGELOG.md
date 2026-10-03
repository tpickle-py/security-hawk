# Changelog

All notable changes to Security Hawk will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
