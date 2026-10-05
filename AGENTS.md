# Developer & AI Agent Guidelines for Security Hawk

This document serves as the primary technical reference for AI coding agents and human contributors working within the `security-hawk` repository.

---

## 1. System Architecture & Repositories

Security Hawk operates as an integrated Home Assistant ecosystem split across two repositories:

1. **`tpickle-py/security-hawk` (This Repository)**:
   - Application source code: Django 5 ASGI backend, Daphne server, Django Channels WebSocket relay, and Vue 3 + TypeScript frontend.
   - Home Assistant Add-on container definition (`Dockerfile`, `run.sh`, `config.yaml`).
   - GitHub Actions workflow (`deploy.yaml`) that builds multi-architecture Docker images (`linux/amd64`, `linux/arm64`) and pushes them to GHCR (`ghcr.io/tpickle-py/security-hawk/{arch}`).
   - Dispatches an automated update event to `ha-addons` upon release.

2. **`tpickle-py/ha-addons` (Add-on Store Catalog)**:
   - Dedicated repository registered by users in Home Assistant (*Settings &rarr; Add-ons &rarr; Add-on Store &rarr; Repositories*).
   - Houses catalog metadata (`repository.yaml`, `.addons.yml`) and add-on definitions (`security_hawk/config.yaml`, `security_hawk/build.yaml`, docs, and icons).
   - Automatically updated on new releases via `hassio-addons/repository-updater`.

---

## 2. Directory Structure

```
security-hawk/
├── backend/                  # Python 3.12+ Django project
│   ├── ha/                   # Home Assistant REST & WebSocket client, area/entity registry, proxy views
│   ├── kiosk/                # Route B Kiosk middleware, token auth, read-only enforcement
│   ├── live/                 # Channels WebSocket consumers, state manager, camera workers
│   ├── mcp/                  # Model Context Protocol (MCP) AI server (JSON-RPC 2.0 & REST tools)
│   ├── plans/                # Floor plan storage, SVG sanitizer, schema migrations, REST API
│   ├── rules/                # Compound rule engine, background queue, action plugins (email, webhook, etc.)
│   ├── securityhawk/         # Django settings, ASGI/WSGI entrypoints, root URL router
│   └── settings_mgr/         # User preferences and integration settings storage
├── frontend/                 # Vue 3 + Vite + TypeScript SPA
│   ├── src/                  # Components (CAD command bar, context menu, dockable panels, canvas), stores, API
│   └── dist/                 # Production build output (copied to backend/static/frontend/)
├── security_hawk/            # Mirrored add-on files consumed by repository-updater
│   ├── config.yaml           # Add-on configuration manifest (init: false, hassio_api: true)
│   ├── build.yaml            # Multi-arch base image configuration
│   ├── DOCS.md               # User documentation visible in HA Add-on Store
│   └── translations/         # Option translations
├── scripts/
│   └── bump_version.py       # Automated semantic version bumper using `uv version`
├── tests/                    # Unit and integration test suite
├── Dockerfile                # Multi-stage container build (Node frontend -> Python backend)
├── run.sh                    # Container entrypoint with s6-overlay / bashio configuration
├── config.yaml               # Root add-on configuration manifest
├── pyproject.toml            # uv project definition, dependencies, ruff, pytest, and coverage config
└── CHANGELOG.md              # Keep-a-Changelog formatted release history
```

---

## 3. Development Commands

### Environment Setup
Python dependencies and virtual environments are managed using `uv`:
```bash
# Sync virtualenv and dependencies
uv sync

# Run backend development server
uv run python backend/manage.py runserver
```

### Running Tests & Linting
Pytest and Coverage configurations are consolidated in `pyproject.toml`:
```bash
# Run pytest with coverage (scripts/ is excluded)
uv run pytest

# Run linter
uv run ruff check .

# Automatically apply safe lint fixes
uv run ruff check --fix .
```

### Frontend Development
```bash
cd frontend
npm install
npm run dev    # Vite dev server with HMR
npm run build  # Compiles and copies bundle into backend/static/frontend/
```

> [!NOTE]
> **Execution Rule for Agents**: `npm run build` executes `vue-tsc -b` type checking followed by `vite build`. Depending on system load, full compilation may take 10–25 seconds. When running `npm run build` via `run_command`, **always launch it in the background** (`WaitMsBeforeAsync: 500`) to prevent synchronous timeout cancellations. You will be notified automatically when the background task finishes. For quick incremental syntax checks without waiting for full bundle bundling, run `npx vite build` or `npx vue-tsc --noEmit`.


---

## 4. Semantic Version Bumping & Release Workflow

> [!IMPORTANT]
> **No Frontend Build Needed During Release**: When bumping versions or cutting releases, **DO NOT run `npm run build`**. `frontend/dist/` and `backend/static/frontend/` are `.gitignore`d. Docker images automatically build the production bundle from source via multi-stage build in CI (`Dockerfile`). Running `npm run build` locally after version bumps is completely unnecessary and can hang tool execution due to local lock contention.

When bumping versions, **do not manually edit individual files**. Use the automated script:

```bash
# Bump patch version (e.g. 0.3.4 -> 0.3.5)
python3 scripts/bump_version.py patch -m "Description of fixes"

# Bump minor version (e.g. 0.3.4 -> 0.4.0)
python3 scripts/bump_version.py minor -m "New feature description"

# Set an explicit version
python3 scripts/bump_version.py 0.4.0

# Preview changes without modifying files
python3 scripts/bump_version.py patch --dry-run
```

### What `scripts/bump_version.py` Updates:
1. Calls `uv version --bump <target>`, updating `pyproject.toml` and `uv.lock`.
2. Synchronizes the new version string across:
   - `config.yaml` (root add-on manifest)
   - `security_hawk/config.yaml` (app subdir manifest for updater)
   - `frontend/package.json`
   - `Dockerfile` (`io.hass.version` label)
   - `CHANGELOG.md` (prepends new version heading with timestamp)
   - `security_hawk/CHANGELOG.md` (app mirror consumed by repository-updater)
   - `../ha-addons/security_hawk/config.yaml` (if present in adjacent directory)
   - `../ha-addons/security_hawk/CHANGELOG.md` (if present in adjacent directory)

### Publishing a Release:
```bash
# 1. Commit and push changes
git add -A
git commit -m "chore(release): vX.Y.Z"

# 2. Tag and push tag
git tag vX.Y.Z
git push origin master && git push origin vX.Y.Z

# 3. If ../ha-addons was modified:
cd ../ha-addons
git add security_hawk/config.yaml security_hawk/CHANGELOG.md
git commit -m "chore: bump security_hawk to X.Y.Z"
git push origin main
```

4. **Publish GitHub Release**:
   - Go to `https://github.com/tpickle-py/security-hawk/releases/new`.
   - Select tag `vX.Y.Z`, enter title `vX.Y.Z`, paste changelog notes, and click **Publish release**.
   - This triggers `.github/workflows/deploy.yaml` which builds the multi-arch GHCR containers and dispatches the update to `ha-addons`.

---

## 5. Critical Technical Constraints & Gotchas

1. **`init: false` in `config.yaml`**:
   - Home Assistant Supervisor defaults to `init: true` (injecting `docker-init` as PID 1).
   - Because the container uses Home Assistant base images with `s6-overlay`, s6 requires being PID 1.
   - If `init: false` is omitted, the container crashes instantly with `s6-overlay-suexec: fatal: can only run as pid 1`.

2. **`hassio_api: true`, `auth_api: true`, and `hassio_role: homeassistant` in `config.yaml`**:
   - Required for Supervisor to inject `SUPERVISOR_TOKEN` with permissions to query Home Assistant Core and Supervisor endpoints.
   - Setting `hassio_role: default` lacks required scopes and results in `403 Forbidden` (`Unable to access the API, forbidden`).

3. **`with-contenv` Shebang & Container Environment**:
   - `s6-overlay` saves container environment variables under `/var/run/s6/container_environment/`.
   - `run.sh` must use `#!/usr/bin/with-contenv bashio` (and import from `/var/run/s6/container_environment/` as fallback) so `SUPERVISOR_TOKEN` is passed to bashio and child processes.

4. **`SUPERVISOR_TOKEN` Fallback**:
   - In `run.sh`, `SUPERVISOR_TOKEN` is exported as `export SUPERVISOR_TOKEN="${SUPERVISOR_TOKEN:-}"`.
   - Because `run.sh` executes with `set -u` (treat unset variables as error), missing tokens during standalone local container testing will cause an exit if not defaulted.

5. **Ingress Proxy Headers vs `REMOTE_ADDR`**:
   - When Daphne runs with `--proxy-headers`, `request.META["REMOTE_ADDR"]` is set to the client browser IP from `X-Forwarded-For` (e.g. `192.168.87.89`).
   - `IngressMiddleware` must check for `HTTP_X_INGRESS_PATH` or HA proxy IPs rather than strictly matching `REMOTE_ADDR == 172.30.32.2`, otherwise valid Ingress traffic is rejected with 403 Forbidden.

6. **`security_hawk/` Subdirectory Mirror**:
   - `hassio-addons/repository-updater` looks for files inside the directory specified by `target:` in `ha-addons/.addons.yml` (`target: security_hawk`).
   - If files are only in the repository root and `security_hawk/` is absent, the updater fails with `An error occurred while loading the remote app configuration file`.
   - Always ensure changes to `config.yaml`, `CHANGELOG.md`, or `DOCS.md` are reflected in `security_hawk/`.

---

## 6. Subsystem Reference: MCP & Advanced Canvas Architecture

### Model Context Protocol (MCP) Server (`backend/mcp/`)
- **Transport & Endpoints**:
  - `POST /api/mcp/rpc`: JSON-RPC 2.0 endpoint implementing `tools/list` and `tools/call`.
  - `GET /api/mcp/tools` & `POST /api/mcp/execute`: Direct REST tools introspection and execution.
  - `GET /api/mcp/status`: Service discovery and current access control status.
- **Granular Access Control Levels**:
  - `read_only`: Inspect floor plans, query entities, check coverage recommendations.
  - `design_only`: Read access plus creating/updating rooms, sub-areas, and walls.
  - `rules_only`: Read access plus creating/updating compound rules.
  - `full_access`: Unrestricted access across design and rule creation.
  - `disabled`: All MCP requests rejected with 403 Forbidden.
- **Sensitive Data Protection**:
  - All responses automatically strip raw tokens and mask IPv4 addresses (`[REDACTED_IP]`) and authentication headers (`[REDACTED_TOKEN]`).

### AutoCAD Command Bar (`CadCommandBar.vue`)
- Implements a keyboard-first terminal interface with 20+ CAD commands (`WALL`, `ROOM`, `DOOR`, `WINDOW`, `SELECT`, `PAN`, `ZOOM`, `SCALE`, `SAVE`, `UNDO`, `REDO`, etc.).
- Includes autocomplete recommendations, arrow key command history (`Up`/`Down`), docking (`bottom`, `top`, `float`), and a collapsible quick-reference helper drawer.

### Dockable & Minimizable Panels (`EntityPicker.vue`, `PropertyPanel.vue`)
- Dockable to `left`, `right`, or `float`.
- Draggable header bars persist free-floating viewport coordinates (`(x, y)`) in `localStorage`.
- Minimizable into interactive floating badges (`🏷️ Entities (N)`, `📐 Properties & Zones`).
- Positions and dock states can be reset to defaults in Settings.

### Interactive 8-Handle Room Resizing & Dragging (`EditorCanvas.vue`)
- Architectural rooms (both `SubArea` and polygon `Shape` rooms) can be selected and dragged directly across canvas space.
- An interactive bounding box provides 8 resize handles (`NW`, `N`, `NE`, `E`, `SE`, `S`, `SW`, `W`) recalculating vertices dynamically during drag operations.

### Accurate Unassigned Entity Tracking
- Entity picker filters and unassigned counts (`unassigned_entities_count`) immediately reflect hidden or ignored entities and domain filters without requiring a page refresh.

