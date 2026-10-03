"""Plan JSON schema helpers — creation of default plan structures and validation."""

from __future__ import annotations

import uuid


def new_plan_id() -> str:
    """Generate a short unique plan ID."""
    return f"plan_{uuid.uuid4().hex[:8]}"


def new_endpoint_id() -> str:
    """Generate a short unique endpoint ID."""
    return f"ep_{uuid.uuid4().hex[:8]}"


def new_building_id() -> str:
    """Generate a short unique building ID."""
    return f"bld_{uuid.uuid4().hex[:8]}"


def new_floor_id() -> str:
    """Generate a short unique floor ID."""
    return f"flr_{uuid.uuid4().hex[:8]}"


def default_plan(name: str = "New Plan") -> dict:
    """Create a new empty plan with the current schema version."""
    return {
        "schema_version": 1,
        "name": name,
        "overview": {
            "id": "overview",
            "name": "Site Overview",
            "scale": None,
            "background": None,
            "endpoints": [],
        },
        "buildings": [],
    }


def default_building(name: str = "Building") -> dict:
    """Create a new empty building."""
    return {
        "id": new_building_id(),
        "name": name,
        "x": 0,
        "y": 0,
        "floors": [default_floor("Ground Floor")],
    }


def default_floor(name: str = "Floor") -> dict:
    """Create a new empty floor."""
    return {
        "id": new_floor_id(),
        "name": name,
        "scale": None,
        "background": None,
        "shapes": [],
        "endpoints": [],
    }


def default_endpoint(
    entity_id: str,
    endpoint_type: str = "generic",
    label: str = "",
    x: float = 0,
    y: float = 0,
    device_id: str | None = None,
) -> dict:
    """Create a new endpoint for a given HA entity."""
    return {
        "id": new_endpoint_id(),
        "entity_id": entity_id,
        "device_id": device_id,
        "type": endpoint_type,
        "x": x,
        "y": y,
        "rotation": 0,
        "label": label,
        "companions": [],
        "cameras": [],
        "coverage": None,
        "stale_after": None,
    }


def suggest_endpoint_type(domain: str, device_class: str | None = None) -> str:
    """Suggest an endpoint type from an entity's domain and device class.

    Rules:
        binary_sensor + motion → motion
        binary_sensor + door/window/garage_door/opening → door
        camera.* → camera
        everything else → generic
    """
    if domain == "camera":
        return "camera"

    if domain == "binary_sensor" and device_class:
        if device_class == "motion":
            return "motion"
        if device_class in ("door", "window", "garage_door", "opening"):
            return "door"

    return "generic"
