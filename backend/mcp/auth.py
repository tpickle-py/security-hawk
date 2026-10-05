"""Access control and sensitive data protection for MCP AI endpoints."""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from django.http import HttpRequest

from settings_mgr.storage import settings_storage

logger = logging.getLogger(__name__)

# Sensitive pattern regexes for redaction
_IP_REGEX = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_TOKEN_REGEX = re.compile(r"((?:bearer|token|secret|password|api[_-]?key)[\"':\s=]+)([a-zA-Z0-9_\-\.]{8,})", re.IGNORECASE)


def get_mcp_config() -> dict[str, Any]:
    """Retrieve MCP configuration from settings storage."""
    settings_data = settings_storage.load()
    mcp_conf = settings_data.get("mcp", {})
    return {
        "enabled": mcp_conf.get("enabled", True),
        "access_level": mcp_conf.get("access_level", "full_access"),
        "api_key": mcp_conf.get("api_key", ""),
        "mask_sensitive_data": mcp_conf.get("mask_sensitive_data", True),
        "allowed_domains": mcp_conf.get(
            "allowed_domains",
            ["camera", "binary_sensor", "sensor", "lock", "alarm_control_panel", "siren"],
        ),
    }


def verify_mcp_request(request: HttpRequest, action_category: str = "read") -> tuple[bool, str]:
    """Verify if the request has sufficient permissions for the requested action category.

    Categories:
      - 'read': inspecting layout, querying entities, listing rules
      - 'design': creating/updating rooms, walls, subareas, layouts
      - 'rules': creating/updating compound rules and action triggers
    """
    conf = get_mcp_config()

    if not conf["enabled"] or conf["access_level"] == "disabled":
        return False, "MCP AI endpoint is disabled in Security Hawk settings."

    # Validate API key if configured
    required_key = conf.get("api_key", "").strip()
    if required_key:
        auth_header = request.headers.get("Authorization", "")
        x_key = request.headers.get("X-MCP-Key", "")
        provided_key = ""
        if auth_header.lower().startswith("bearer "):
            provided_key = auth_header[7:].strip()
        elif x_key:
            provided_key = x_key.strip()

        if provided_key != required_key:
            return False, "Unauthorized: Invalid or missing MCP API key."

    access_level = conf["access_level"]

    if action_category == "read":
        # All active levels can read
        return True, ""

    if action_category == "design":
        if access_level in ("design_only", "full_access"):
            return True, ""
        return False, f"Permission Denied: Current MCP access level is '{access_level}', which forbids design layout mutations."

    if action_category == "rules":
        if access_level in ("rules_only", "full_access"):
            return True, ""
        return False, f"Permission Denied: Current MCP access level is '{access_level}', which forbids compound rule mutations."

    return False, f"Unknown action category: {action_category}"


def sanitize_text(text: str) -> str:
    """Mask IP addresses and credential tokens in freeform strings."""
    if not isinstance(text, str):
        return text
    text = _IP_REGEX.sub("[REDACTED_IP]", text)
    text = _TOKEN_REGEX.sub(r"\1[REDACTED_TOKEN]", text)
    return text


def sanitize_entity(entity: dict[str, Any], mask_sensitive: bool = True) -> dict[str, Any]:
    """Return a clean entity object with sensitive internal attributes stripped."""
    safe_fields = {
        "entity_id": entity.get("entity_id", ""),
        "name": sanitize_text(entity.get("name") or entity.get("friendly_name") or ""),
        "domain": entity.get("domain") or entity.get("entity_id", "").split(".")[0],
        "state": entity.get("state"),
        "area_id": entity.get("area_id"),
        "device_class": entity.get("device_class") or entity.get("attributes", {}).get("device_class"),
    }
    if not mask_sensitive:
        safe_fields["attributes"] = entity.get("attributes", {})
    return safe_fields


def sanitize_plan_layout(plan: dict[str, Any], mask_sensitive: bool = True) -> dict[str, Any]:
    """Sanitize plan structure for AI consumption."""
    result = {
        "id": plan.get("id"),
        "name": plan.get("name"),
        "schema_version": plan.get("schema_version"),
        "sub_areas": plan.get("sub_areas", []),
        "shapes": plan.get("shapes", []),
        "endpoints": [],
    }

    # Redact sensitive background URLs or local file system tokens if needed
    bg = plan.get("background")
    if bg:
        result["background"] = {
            "width": bg.get("width"),
            "height": bg.get("height"),
            "locked": bg.get("locked"),
        }

    for ep in plan.get("endpoints", []):
        safe_ep = {
            "id": ep.get("id"),
            "entity_id": ep.get("entity_id"),
            "type": ep.get("type"),
            "label": sanitize_text(ep.get("label", "")),
            "x": ep.get("x"),
            "y": ep.get("y"),
            "rotation": ep.get("rotation", 0),
            "coverage": ep.get("coverage"),
            "group_name": sanitize_text(ep.get("group_name") or "") if ep.get("group_name") else None,
        }
        result["endpoints"].append(safe_ep)

    return result
