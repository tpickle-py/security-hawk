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
│   ├── plans/                # Floor plan storage, SVG sanitizer, schema migrations, REST API
│   ├── rules/                # Compound rule engine, background queue, action plugins (email, webhook, etc.)
│   ├── securityhawk/         # Django settings, ASGI/WSGI entrypoints, root URL router
│   └── settings_mgr/         # User preferences and integration settings storage
├── frontend/                 # Vue 3 + Vite + TypeScript SPA
│   ├── src/                  # Components, Pinia stores, router, API client
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

---

## 4. Semantic Version Bumping & Release Workflow

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
   - `../ha-addons/security_hawk/config.yaml` (if present in adjacent directory)

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
git add security_hawk/config.yaml
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
   - Always ensure changes to `config.yaml` or `DOCS.md` are reflected in `security_hawk/`.
