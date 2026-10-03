# Security Hawk

<div align="center">

![Tests](https://img.shields.io/badge/tests-23%20passed-success?style=for-the-badge&logo=pytest&logoColor=white)
![Coverage](https://img.shields.io/badge/coverage-pytest--cov%2060%25-informational?style=for-the-badge&logo=codecov&logoColor=white)
![Python](https://img.shields.io/badge/python-3.12%2B-blue?style=for-the-badge&logo=python&logoColor=white)
![Django](https://img.shields.io/badge/django-5.2%2B-092E20?style=for-the-badge&logo=django&logoColor=white)
![Vue.js](https://img.shields.io/badge/vue.js-3.5%2B-4FC08D?style=for-the-badge&logo=vue.js&logoColor=white)
![Vite](https://img.shields.io/badge/vite-6.0-646CFF?style=for-the-badge&logo=vite&logoColor=white)
![Ruff](https://img.shields.io/badge/linter-ruff-black?style=for-the-badge&logo=ruff&logoColor=white)
![uv](https://img.shields.io/badge/package%20manager-uv-DE5FE9?style=for-the-badge&logo=astral&logoColor=white)
![Home Assistant](https://img.shields.io/badge/home%20assistant-app%20%2F%20add--on-41BDF5?style=for-the-badge&logo=home-assistant&logoColor=white)

**Floor plan viewer with real-time sensor state, live camera streaming, nested zones, and unattended TV display for Home Assistant**

</div>

---

## Highlights & Features

- **Design Mode & Canvas**:
  - **Background Upload**: Upload architectural floor plans (sanitized SVGs, PNG, JPEG, WebP).
  - **Scale Calibration**: Two-point real-world scale calibration in metres.
  - **Box & Marquee Drag Selection**: Drag across empty canvas to select multiple entities at once, with `Shift` modifier support.
  - **Synchronized Multi-Move**: Drag any selected endpoint to move the entire selection across the canvas simultaneously.
  - **Version History**: Rolling 20-save version history with one-click restore.
- **Nested Areas & Entities**:
  - **Area within an Area (Sub-Areas / Zones)**: Define custom room zones and nested sub-areas (e.g. Walk-in Closet inside Master Bedroom) assigned to parent Home Assistant rooms.
  - **Entity within an Entity (Nested Endpoints)**: Attach sensors directly to other endpoints (e.g. vibration sensor attached to a door, or multi-sensor attached to a camera).
  - **Duplicate Placements**: Place the same Home Assistant entity at more than one spot on the canvas with live concurrent state synchronization.
  - **Group into Unified Units**: Group multiple endpoints into a single named unit with group indicators (`G` badge).
- **Architectural Door & Window Representations**:
  - **Doors**: Distinct closed state (frame and door leaf) vs open state (amber warning glow with 90° dotted swing arc).
  - **Windows**: Distinct closed state (4-pane sash) vs open state (slid-open sash with air draft chevrons and warning glow).
  - **Quick Rotation**: 90° clockwise/counter-clockwise step buttons and 360° precision slider.
- **Room & Area Designation**:
  - Automatic discovery of all Home Assistant rooms and areas (`config/area_registry/list`).
  - Highlights unassigned entities with instant room designation directly inside the picker.
  - Filter entities by room or unassigned status.
- **Friendly Name & Entity Search**:
  - Full-text search matching Home Assistant friendly names, room/area names, and entity IDs.
  - Friendly names displayed prominently across design, inspector, and live views.
- **Remote & Browser Camera Navigation**:
  - Full keyboard accessibility and Google TV / Android TV remote control D-pad navigation.
  - Tab or directional arrow navigation across sensors and cameras on the floor plan with high-contrast focus rings.
  - Click or press `Enter` / `Space` on any camera to launch a windowed live snapshot viewer.
  - Press `Escape` or the TV remote `Back` button to dismiss the window.
- **Usage & Live View Mode**:
  - Sub-second update latency over persistent WebSocket relay.
  - Animated pulsing alert waves for active motion, doors, and windows.
- **Route B Kiosk Mode (TV Display)**:
  - Direct kiosk port with token authentication (`http://<ha-host>:<kiosk_port>/kiosk/?token=<token>`).
  - Read-only enforcement, unattended 24/7 reliability, auto-reconnect banner on network drops, and quiet return to overview.

---

## Projects & Technologies Used

### Backend
- **[Python 3.12+](https://www.python.org/)** — Core programming language
- **[Django 5.2+](https://www.djangoproject.com/)** — REST API framework and application scaffolding
- **[Daphne](https://github.com/django/daphne)** & **[Django Channels](https://channels.readthedocs.io/)** — ASGI WebSocket server delivering live state changes
- **[WebSockets](https://websockets.readthedocs.io/)** & **[aiohttp](https://docs.aiohttp.org/)** — Asynchronous Home Assistant Core API & Supervisor event bridge
- **[defusedxml](https://github.com/tiran/defusedxml)** — Hardened XML parser providing SVG sanitization (stripping scripts and malicious payloads)
- **[Pillow](https://python-pillow.org/)** — Image handling and dimensions
- **[uv](https://github.com/astral-sh/uv)** — Ultra-fast Python package and virtualenv manager
- **[Ruff](https://github.com/astral-sh/ruff)** — Fast linter and code formatter
- **[pytest](https://pytest.org/)** & **[pytest-cov](https://pytest-cov.readthedocs.io/)** — Unit test suite with line-by-line coverage analysis

### Frontend
- **[Vue 3](https://vuejs.org/)** — Composition API single-page application
- **[TypeScript 5.7+](https://www.typescriptlang.org/)** — Type-safe contracts matching the plan data model
- **[Vite 6](https://vitejs.dev/)** — Frontend bundler with sub-second HMR and production optimization
- **[Pinia](https://pinia.vuejs.org/)** — Reactive state management stores (`planStore`, `liveStore`, `entityStore`, `editorStore`)
- **[Vue Router 4](https://router.vuejs.org/)** — Hash-based routing ensuring seamless compatibility with Home Assistant Ingress
- **Vanilla CSS Design System** — Tailored modern dark mode theme with glassmorphism and micro-animations

### Home Assistant Integration
- **Home Assistant Supervisor App Architecture** (`config.yaml`, `Dockerfile`, `run.sh`)
- **Ingress Support** with reverse-proxy IP validation (`172.30.32.2`) and dynamic path injection
- **Entity Registry & Area Registry integration** (`config/entity_registry/list_for_display`, `config/area_registry/list`)

---

## How to Use: First Steps & Walkthroughs

### 1. First Steps: Getting Started

1. **Install and Open**: Launch Security Hawk through Home Assistant or open the local dev server.
2. **Upload Floor Plan Background**:
   - In the top toolbar, click **Background**.
   - Select an architectural drawing, SVG, or image of your floor.
   - The image is sanitized and centered on the canvas.
3. **Calibrate Real-World Scale**:
   - Click the **Calibrate Scale** (ruler) icon in the toolbar.
   - Click two points on the plan whose distance you know (e.g. a 3-metre wall or 1-metre doorway).
   - Enter the measurement in metres and click **Save Scale**.
4. **Place Sensors & Cameras**:
   - Open the **Entity Picker** on the left.
   - Search for devices by friendly name or room.
   - Drag items directly onto the canvas.

---

### 2. Next Steps & Advanced Workflows

#### A. Marquee Selection & Moving Multiple Items
- **Box Selection**: Click and drag on empty canvas space to draw a marquee box around the endpoints you want to select.
- **Additive Selection**: Hold `Shift` while dragging or clicking endpoints to add them to your selection.
- **Synchronized Movement**: Click and drag **any** selected endpoint. All selected items move together smoothly while preserving their relative positions.
- **Bulk Actions**: With multiple items selected, the right Property Panel provides one-click grouping, ungrouping, and bulk deletion.

#### B. Grouping Entities into One Unit
1. Select multiple endpoints using box selection or `Shift`-click.
2. In the Property Panel on the right, under **Group Into Unit**, type a name (e.g. `Master Suite Sensors` or `Front Entryway`).
3. Click **🔗 Group as Single Unit**.
4. Grouped endpoints display a prominent `G` badge on the canvas.
5. To disband the group later, select the items and click **🔓 Ungroup Selected Items**.

#### C. Area within an Area (Nested Sub-Areas / Zones)
1. Deselect any endpoints so the Property Panel displays **Floor Areas & Zones**.
2. Under **Add Sub-Area / Zone**, enter a name (e.g. `Ensuite Bathroom` or `Walk-in Closet`).
3. Optional: Select a **Parent Area** from your Home Assistant rooms (e.g. `Master Bedroom`).
4. Click **+ Add Sub-Area to Floor**.
5. The sub-area appears on the floor plan with distinct dashed zone borders and labels in both design and live monitoring views.

#### D. Entity within an Entity (Nested Endpoints)
1. Click on an endpoint you want to attach (e.g. a vibration/tilt sensor or multi-sensor).
2. In the Property Panel, locate **Nest Within Parent Entity**.
3. Choose the parent endpoint from the dropdown (e.g. `Front Door (door)` or `Driveway Cam (camera)`).
4. The child endpoint now displays an amber nested indicator pip, establishing a hierarchical connection.

#### E. Duplicate Entities at Multiple Spots
- If you have an entity that logically belongs in more than one location (e.g. an alarm panel status, multi-zone occupancy, or shared sensor), simply drag it from the left **Entity Picker** again.
- The picker displays a badge showing `Placed ×N` while remaining draggable.
- Each canvas placement maintains its own position and rotation while both instances receive real-time state broadcasts simultaneously.

#### F. Doors vs. Windows (Open vs. Shut Visuals)
- Select any door or window endpoint on the canvas.
- In the Property Panel under **Endpoint Type**, choose **Door** or **Window**.
- Use the quick `↺ -90°` and `↻ +90°` buttons to orient the opening direction.
- In **Live Mode**:
  - **Door Closed**: Dark jamb with panels and door knob.
  - **Door Open**: Amber alert glow with 90° dotted swing arc indicating the open swing path.
  - **Window Closed**: 4-pane architectural sash.
  - **Window Open**: Slid-open sash with air draft chevrons and warning glow.

#### G. TV Remote & D-Pad Keyboard Navigation
- In **Live Mode** (or Kiosk display), you can navigate entirely without a mouse:
  - **Tab / Shift+Tab**: Cycles through all interactive endpoints with high-contrast glowing focus rings.
  - **Arrow Keys (D-Pad)**: Press `Up`, `Down`, `Left`, or `Right` on your Google TV remote or keyboard. The system computes spatial geometry to jump directly to the nearest physical endpoint in that direction.
  - **Enter / OK Button**: Opens a windowed live snapshot feed for camera endpoints.
  - **Escape / Back Button**: Dismisses the camera viewer and returns to the floor overview.

---

## Installation & Running

### As a Home Assistant App

1. Add this repository to your Home Assistant Add-on / App Store.
2. Click **Install**.
3. In the configuration tab, configure kiosk options if TV display is desired:
   ```yaml
   kiosk_enabled: true
   kiosk_port: 8100
   kiosk_token: "your-secure-token"
   default_view: "overview"
   quiet_return_seconds: 120
   ```
4. Click **Start** and then **Open Web UI**.

### Local Development

1. **Clone the repository:**
   ```bash
   git clone https://github.com/tpickle/security-hawk.git
   cd security-hawk
   ```

2. **Backend Setup (Python + uv):**
   ```bash
   uv sync
   uv run python backend/manage.py runserver
   ```

3. **Frontend Setup (Vue + Vite):**
   ```bash
   cd frontend
   npm install
   npm run dev    # For dev server
   npm run build  # For production build syncing to backend static
   ```

4. **Run Tests & Linting:**
   ```bash
   # Run tests with coverage
   uv run pytest tests --cov=backend

   # Run linter checks
   uv run ruff check .
   ```

---

## Keyboard & Remote Navigation Cheatsheet

| Key / Control | Action |
| --- | --- |
| `Tab` / `Shift+Tab` | Cycle through interactive sensor and camera endpoints |
| `ArrowUp` / `Down` / `Left` / `Right` | Directional D-pad jump to the nearest physical endpoint |
| `Enter` / `Space` | Activate endpoint (opens windowed camera feed for cameras) |
| `Escape` / `Back` (TV remote) | Dismiss windowed camera view and return to floor plan |

---

## License

MIT License. See [DOCS.md](DOCS.md) for full documentation and architectural specifications.
