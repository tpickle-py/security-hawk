# Security Hawk Documentation

## Getting Started

### Requirements

- Home Assistant 2026.2 or later (with app/add-on support)
- A browser for the editor (any modern browser)
- For TV display: Google TV device with a browser or kiosk app

### Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `kiosk_enabled` | `false` | Enable the direct kiosk port for TV display |
| `kiosk_port` | `8100` | Port number for the kiosk page |
| `kiosk_token` | (auto-generated) | Secret token required in the kiosk URL |
| `default_view` | `overview` | View the kiosk page opens on (`overview` or `floor`) |
| `quiet_return_seconds` | `120` | Follow-activity mode returns to the overview after this many seconds |

## Design Mode

### Uploading a Background

1. Click the **Background** tool in the toolbar
2. Upload an SVG, PNG, JPG, or PDF file
3. Position and resize the background as needed
4. Lock it in place

### Setting the Scale

1. Click the **Scale** tool
2. Click two points on the plan whose real-world distance you know
3. Enter the real distance in metres
4. The scale is saved and used for sizing endpoints and coverage areas

### Placing Endpoints & Advanced Features

1. Open the **Entity Picker** panel.
2. Search for a Home Assistant entity by friendly name, room, or filter by domain.
3. Drag the entity onto the floor plan.
4. **Duplicate Placements**: Place the same entity at multiple spots on the floor plan; all instances sync state concurrently.
5. **Door & Window Distinction**: Set the type to "Door" or "Window". Doors feature swing arc representations when open; windows feature open-sash and airflow indicators.
6. **Entity Nesting**: Attach an entity as a child to another endpoint (e.g., vibration sensor on a door or sensor on a camera).
7. **Unit Grouping**: Select multiple endpoints using marquee drag or Shift-click, and click **Group as Single Unit** to assign a shared unit identifier.
8. **Sub-Areas / Nested Rooms**: Define rooms within rooms (sub-areas) and attach them to parent Home Assistant areas.

## Usage Mode (Live View)

The live view shows your floor plan with real-time state from Home Assistant:

- **Motion sensors**: Pulse animation when detected, dim when clear
- **Doors**: Distinct closed frame vs. open door leaf with 90° dotted swing arc and amber warning glow
- **Windows**: Distinct 4-pane closed sash vs. slid-open sash with air draft chevrons and amber alert glow
- **Cameras**: Camera icon; click or press `Enter`/`Space` to open a windowed live snapshot modal
- **TV Remote Navigation**: Full D-pad arrow key and Tab navigation with glowing focus rings; press `Escape` or `Back` on TV remote to dismiss modal
- **Unavailable entities**: Grey icon with question mark
- **Grouped Units**: Indicated with a `G` badge
- **Companion entities**: Small badge on the parent endpoint (e.g., low battery)

## Kiosk Mode

The kiosk page is a full-screen, no-menu version of the live view designed for TVs.

### Setup

1. Enable kiosk mode in the app configuration
2. Note the kiosk token from the app logs (or set your own)
3. Open the kiosk URL on your TV: `http://<ha-ip>:<kiosk_port>/kiosk/?token=<token>`

### Behaviour

- Auto-reconnects after network drops or HA restarts
- Shows a clear "Disconnected" banner when live data is unavailable
- No editing controls — read-only

## Security Notes

- The editor is only accessible through Home Assistant ingress (requires HA login)
- The kiosk page is off by default and requires a secret token
- The Supervisor token never reaches the browser
- Uploaded SVG files are sanitized (scripts and event handlers are stripped)
- The app makes no outbound internet connections

## Data Storage

Plans are stored as JSON files in `/data/plans/` inside the app container. This directory is included in Home Assistant backups. The last 20 saved versions of each plan are kept for rollback in `/data/versions/`.
