# Changelog

All notable changes to Security Hawk will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
