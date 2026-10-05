"""Tool definitions and executors for Security Hawk Model Context Protocol (MCP)."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from django.conf import settings

from ha.registry import entity_registry
from mcp.auth import sanitize_entity, sanitize_plan_layout
from plans.storage import PlanStorage
from rules.storage import RulesStorage

logger = logging.getLogger(__name__)


def _get_plan_storage() -> PlanStorage:
    data_dir = getattr(settings, "DATA_DIR", "/data")
    return PlanStorage(f"{data_dir}/plans", f"{data_dir}/versions")


def _get_rules_storage() -> RulesStorage:
    return RulesStorage()


# Tool metadata schemas matching MCP specifications
MCP_TOOL_DEFINITIONS = [
    {
        "name": "get_floor_plan",
        "description": "Retrieve the current floor plan layout, architectural rooms, walls, sub-areas, and placed sensors.",
        "category": "read",
        "parameters": {
            "type": "object",
            "properties": {
                "plan_id": {
                    "type": "string",
                    "description": "Optional ID of specific floor plan to retrieve. If omitted, uses the default or primary plan.",
                }
            },
        },
    },
    {
        "name": "get_available_entities",
        "description": "List Home Assistant entities available for placement on the floor plan (cameras, motion sensors, door contacts, locks, etc.).",
        "category": "read",
        "parameters": {
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "description": "Optional domain filter (e.g. 'camera', 'binary_sensor', 'lock').",
                }
            },
        },
    },
    {
        "name": "get_compound_rules",
        "description": "List all configured multi-sensor compound rules and trigger conditions.",
        "category": "read",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "add_room",
        "description": "Add an architectural room polygon boundary to the floor plan.",
        "category": "design",
        "parameters": {
            "type": "object",
            "required": ["name", "points"],
            "properties": {
                "name": {"type": "string", "description": "Name of the room (e.g. 'Living Room', 'Server Room')."},
                "points": {
                    "type": "array",
                    "description": "List of [x, y] coordinate pairs defining the room polygon vertices.",
                    "items": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 2,
                        "maxItems": 2,
                    },
                },
                "plan_id": {"type": "string", "description": "Target floor plan ID."},
                "fill": {"type": "string", "description": "Optional CSS fill color (e.g. 'rgba(99, 102, 241, 0.12)')."},
                "stroke": {"type": "string", "description": "Optional CSS border color (e.g. '#6366f1')."},
            },
        },
    },
    {
        "name": "add_subarea",
        "description": "Add a rectangular sub-area or zone (e.g. closet, pantry, entryway) to the floor plan.",
        "category": "design",
        "parameters": {
            "type": "object",
            "required": ["name", "x", "y", "width", "height"],
            "properties": {
                "name": {"type": "string", "description": "Name of the sub-area / zone."},
                "x": {"type": "number", "description": "Top-left X coordinate."},
                "y": {"type": "number", "description": "Top-left Y coordinate."},
                "width": {"type": "number", "description": "Width in pixels."},
                "height": {"type": "number", "description": "Height in pixels."},
                "parent_area_id": {"type": "string", "description": "Optional parent area ID for nesting."},
                "plan_id": {"type": "string", "description": "Target floor plan ID."},
            },
        },
    },
    {
        "name": "add_wall",
        "description": "Add an architectural wall segment between two points on the floor plan.",
        "category": "design",
        "parameters": {
            "type": "object",
            "required": ["x1", "y1", "x2", "y2"],
            "properties": {
                "x1": {"type": "number", "description": "Start X coordinate."},
                "y1": {"type": "number", "description": "Start Y coordinate."},
                "x2": {"type": "number", "description": "End X coordinate."},
                "y2": {"type": "number", "description": "End Y coordinate."},
                "thickness": {"type": "number", "description": "Wall thickness in pixels (default 8)."},
                "plan_id": {"type": "string", "description": "Target floor plan ID."},
            },
        },
    },
    {
        "name": "create_compound_rule",
        "description": "Create a multi-sensor compound rule with boolean conditions (AND/OR) and actions.",
        "category": "rules",
        "parameters": {
            "type": "object",
            "required": ["name", "triggers"],
            "properties": {
                "name": {"type": "string", "description": "Descriptive name for the compound rule."},
                "condition_logic": {
                    "type": "string",
                    "enum": ["AND", "OR"],
                    "description": "Boolean evaluation logic for triggers (default 'AND').",
                },
                "triggers": {
                    "type": "array",
                    "description": "List of entity triggers with expected states.",
                    "items": {
                        "type": "object",
                        "required": ["entity_id", "to_state"],
                        "properties": {
                            "entity_id": {"type": "string"},
                            "to_state": {"type": "string"},
                            "within_seconds": {"type": "number"},
                        },
                    },
                },
                "actions": {
                    "type": "array",
                    "description": "Optional list of actions to fire when the rule triggers.",
                    "items": {
                        "type": "object",
                        "required": ["type"],
                        "properties": {
                            "type": {"type": "string", "enum": ["ha_service", "webhook", "email", "mqtt"]},
                            "config": {"type": "object"},
                        },
                    },
                },
                "output_entity_id": {
                    "type": "string",
                    "description": "Optional custom binary sensor entity ID (defaults to 'binary_sensor.security_hawk_<rule_id>').",
                },
            },
        },
    },
    {
        "name": "validate_security_coverage",
        "description": "Analyze the floor plan layout for security gaps, unmonitored doors, and missing camera coverage.",
        "category": "read",
        "parameters": {
            "type": "object",
            "properties": {
                "plan_id": {"type": "string", "description": "Optional target floor plan ID."},
            },
        },
    },
]


# Tool Implementations
def execute_tool(name: str, arguments: dict[str, Any], mask_sensitive: bool = True) -> dict[str, Any]:
    """Execute a registered MCP tool by name."""
    storage = _get_plan_storage()

    if name == "get_floor_plan":
        plan_id = arguments.get("plan_id")
        if not plan_id:
            plans = storage.list_plans()
            if not plans:
                return {"error": "No floor plans exist yet."}
            plan_id = plans[0]["id"]

        plan = storage.load(plan_id)
        if not plan:
            return {"error": f"Floor plan '{plan_id}' not found."}
        return {"plan": sanitize_plan_layout(plan, mask_sensitive=mask_sensitive)}

    elif name == "get_available_entities":
        domain_filter = arguments.get("domain", "")
        limit = arguments.get("limit", 200)
        try:
            entities = entity_registry.search(domain=domain_filter, limit=limit)
            sanitized = [sanitize_entity(e, mask_sensitive=mask_sensitive) for e in entities]
            return {"entities": sanitized, "count": len(sanitized)}
        except Exception as e:
            logger.warning("Could not search entity registry: %s", e)
            return {"entities": [], "error": f"Entity registry error: {e}"}

    elif name == "get_compound_rules":
        rules_storage = _get_rules_storage()
        rules = rules_storage.list_rules()
        return {"rules": rules, "count": len(rules)}

    elif name == "add_room":
        plan_id = arguments.get("plan_id")
        if not plan_id:
            plans = storage.list_plans()
            if not plans:
                return {"error": "No floor plan available to add room."}
            plan_id = plans[0]["id"]

        plan = storage.load(plan_id)
        if not plan:
            return {"error": f"Floor plan '{plan_id}' not found."}

        room_id = f"shape_rm_{uuid.uuid4().hex[:8]}"
        new_room = {
            "id": room_id,
            "type": "room",
            "geometry": {
                "name": arguments["name"],
                "points": arguments["points"],
            },
            "style": {
                "fill": arguments.get("fill", "rgba(99, 102, 241, 0.12)"),
                "stroke": arguments.get("stroke", "#6366f1"),
                "strokeWidth": 1.5,
            },
        }
        shapes = plan.get("shapes", [])
        shapes.append(new_room)
        plan["shapes"] = shapes
        storage.save(plan_id, plan)
        return {"success": True, "room_id": room_id, "room": new_room}

    elif name == "add_subarea":
        plan_id = arguments.get("plan_id")
        if not plan_id:
            plans = storage.list_plans()
            if not plans:
                return {"error": "No floor plan available to add sub-area."}
            plan_id = plans[0]["id"]

        plan = storage.load(plan_id)
        if not plan:
            return {"error": f"Floor plan '{plan_id}' not found."}

        subarea_id = f"sub_{uuid.uuid4().hex[:8]}"
        new_subarea = {
            "id": subarea_id,
            "name": arguments["name"],
            "x": arguments["x"],
            "y": arguments["y"],
            "width": arguments["width"],
            "height": arguments["height"],
            "parent_area_id": arguments.get("parent_area_id"),
            "color": "rgba(99, 102, 241, 0.15)",
        }
        sub_areas = plan.get("sub_areas", [])
        sub_areas.append(new_subarea)
        plan["sub_areas"] = sub_areas
        storage.save(plan_id, plan)
        return {"success": True, "subarea_id": subarea_id, "sub_area": new_subarea}

    elif name == "add_wall":
        plan_id = arguments.get("plan_id")
        if not plan_id:
            plans = storage.list_plans()
            if not plans:
                return {"error": "No floor plan available to add wall."}
            plan_id = plans[0]["id"]

        plan = storage.load(plan_id)
        if not plan:
            return {"error": f"Floor plan '{plan_id}' not found."}

        wall_id = f"shape_w_{uuid.uuid4().hex[:8]}"
        thickness = arguments.get("thickness", 8)
        new_wall = {
            "id": wall_id,
            "type": "wall",
            "geometry": {
                "x1": arguments["x1"],
                "y1": arguments["y1"],
                "x2": arguments["x2"],
                "y2": arguments["y2"],
                "thickness": thickness,
                "openings": [],
            },
            "style": {
                "stroke": "#475569",
                "strokeWidth": thickness,
            },
        }
        shapes = plan.get("shapes", [])
        shapes.append(new_wall)
        plan["shapes"] = shapes
        storage.save(plan_id, plan)
        return {"success": True, "wall_id": wall_id, "wall": new_wall}

    elif name == "create_compound_rule":
        rules_storage = _get_rules_storage()
        rule_data = {
            "name": arguments["name"],
            "condition_logic": arguments.get("condition_logic", "AND"),
            "triggers": arguments["triggers"],
            "actions": arguments.get("actions", []),
            "output_entity_id": arguments.get("output_entity_id"),
        }
        created = rules_storage.create_or_update(rule_data)
        return {"success": True, "rule": created}

    elif name == "validate_security_coverage":
        plan_id = arguments.get("plan_id")
        if not plan_id:
            plans = storage.list_plans()
            if not plans:
                return {"error": "No floor plan available."}
            plan_id = plans[0]["id"]

        plan = storage.load(plan_id)
        if not plan:
            return {"error": f"Floor plan '{plan_id}' not found."}

        shapes = plan.get("shapes", [])
        endpoints = plan.get("endpoints", [])
        rooms = [s for s in shapes if s.get("type") == "room"]
        sub_areas = plan.get("sub_areas", [])
        walls = [s for s in shapes if s.get("type") == "wall"]

        doors = []
        for w in walls:
            openings = w.get("geometry", {}).get("openings", [])
            for op in openings:
                if op.get("type") == "door":
                    doors.append(op)

        # Analyze coverage
        recommendations = []
        if len(doors) > 0 and len([ep for ep in endpoints if ep.get("type") == "door"]) == 0:
            recommendations.append("Architectural doors found on floor plan, but no door contact sensors are placed.")

        if len(rooms) > 0 and len([ep for ep in endpoints if ep.get("type") == "motion"]) == 0:
            recommendations.append("Rooms configured, but no motion detection sensors are covering the interior spaces.")

        if len([ep for ep in endpoints if ep.get("type") == "camera"]) == 0:
            recommendations.append("No security camera streams or video endpoints positioned on this floor.")

        return {
            "plan_name": plan.get("name", plan_id),
            "stats": {
                "rooms_count": len(rooms),
                "sub_areas_count": len(sub_areas),
                "walls_count": len(walls),
                "door_cutouts_count": len(doors),
                "total_sensors_placed": len(endpoints),
            },
            "recommendations": recommendations,
            "status": "secure" if len(recommendations) == 0 else "action_recommended",
        }

    return {"error": f"Unknown tool: '{name}'"}
