# Home Assistant Add-on: Security Hawk

Interactive multi-floor plan viewer and security monitoring hub for Home Assistant. Features live entity and companion sensor state, low-latency live camera streaming, motion traversal trails, building roll-ups, customizable alert rules, and direct full-screen kiosk mode for wall displays and TVs.

## Table of Contents

- [Installation](#installation)
- [Configuration Options](#configuration-options)
- [How to Use](#how-to-use)
  - [1. Ingress (Editor & Control Panel)](#1-ingress-editor--control-panel)
  - [2. Setting Up Floor Plans](#2-setting-up-floor-plans)
  - [3. Live Monitoring Mode](#3-live-monitoring-mode)
  - [4. Direct Kiosk Mode (TVs & Wall Mounts)](#4-direct-kiosk-mode-tvs--wall-mounts)
- [Features](#features)
  - [Camera Live Video Streaming](#camera-live-video-streaming)
  - [Motion Traversal Trails](#motion-traversal-trails)
  - [Site Overview & Building Roll-Up](#site-overview--building-roll-up)
  - [Compound Rules & Notifications](#compound-rules--notifications)
  - [Floor Plan Bundles (.zip Export / Import)](#floor-plan-bundles-zip-export--import)
- [Data Storage & Backups](#data-storage--backups)
- [Support](#support)

---

## Installation

1. Add this repository to your Home Assistant Add-on Store:
   ```txt
   https://github.com/tpickle-py/ha-addons
   ```
2. In the Add-on Store, find and click **Security Hawk**.
3. Click **Install**.
4. (Optional) Toggle **Show in sidebar** for quick access.
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
- Click **Open Web UI** or select **Security Hawk** from your Home Assistant left sidebar.
- Access is automatically protected by your Home Assistant user credentials and authentication session.
- Allows editing plans, configuring entity placement, managing rules, and adjusting system settings.

### 2. Setting Up Floor Plans

1. **Background**: Upload an architectural floor plan image (PNG, JPG, SVG, or PDF) or start with a blank canvas.
2. **Drawing Tools**: Draw walls with orthogonal angle lock, room polygons with automatic centroid labeling, cutouts for doors/windows, and text labels.
3. **Scale**: Click the **Scale** tool, click two points on your plan with known distance, and specify real-world meters.
4. **Place Endpoints**:
   - Drag sensors, doors, windows, and cameras directly from the Home Assistant entity picker panel onto the plan.
   - Use **⚡ Auto-Detect Companions** to automatically link low battery, tamper, and temperature sensors.
   - Bind cameras to motion and contact sensors for instant alert popups.
   - Adjust detection range and field-of-view (FOV) cones.

### 3. Live Monitoring Mode

Switch from **Design Mode** to **Live Mode** in the toolbar:
- **Motion Sensors**: Animated radar pulse on detection.
- **Doors & Windows**: Architectural 90° swing arcs and open sash status indicators.
- **Cameras**: Windowed live snapshot modal or low-latency MJPEG live stream.
- **Follow-Activity**: Automatically pans and zooms to newly active sensors across floors.
- **TV Remote Navigation**: Full D-pad arrow key and Tab navigation with visible focus rings.

### 4. Direct Kiosk Mode (TVs & Wall Mounts)

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

## Features

### Camera Live Video Streaming
View live cameras directly within floor plan popups. Supports real-time MJPEG proxy streaming directly from Home Assistant with automatic fallback to high-frequency snapshots.

### Motion Traversal Trails
When multiple sensors detect movement in sequence, Security Hawk renders a spatio-temporal flowing gradient trail with numbered checkpoint sequence badges (`#1`, `#2`, `#3`) and elapsed timing indicators.

### Site Overview & Building Roll-Up
Monitor multiple floors or detached buildings simultaneously. A floating HUD summarizes open entry points, active motion, and offline entities across structures.

### Compound Rules & Notifications
Configure multi-condition automations (`ALL` / `ANY`) with sliding time-window correlation. Dispatch notifications to Home Assistant services, SMTP email, WhatsApp (CallMeBot/Twilio), Discord webhooks, Slack, Telegram bot, or custom webhooks.

### Floor Plan Bundles (.zip Export / Import)
Export entire floor plans, custom images, assets, and rules into a single portable `.zip` bundle for easy backup or transfer.

---

## Data Storage & Backups

- Plans, uploaded blueprints, asset images, and version history are stored inside `/data/` in the container.
- The `/data` volume is automatically included in standard Home Assistant backups (Supervisor backups).
- Security Hawk maintains the last 20 rolling versions of each floor plan for rollback safety.

---

## Support

- [GitHub Repository](https://github.com/tpickle-py/security-hawk)
- [Issue Tracker](https://github.com/tpickle-py/security-hawk/issues)
