"""Schema migration engine for Security Hawk floor plans.

Handles versioned plan schema evolution, ensuring plans created in earlier
versions (v1) automatically upgrade to newer structures (v2+) with sensible
defaults, preserving all user data and backward compatibility.
"""

from __future__ import annotations

import copy
import logging
from typing import Any

logger = logging.getLogger(__name__)

CURRENT_SCHEMA_VERSION = 2


def migrate_plan_data(data: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """Migrate plan data to the current schema version.

    Returns:
        tuple[dict, bool]: (migrated_plan_dict, was_modified)
    """
    plan = copy.deepcopy(data)
    initial_version = plan.get("schema_version", 1)
    modified = False

    if initial_version < 2:
        plan = _migrate_v1_to_v2(plan)
        modified = True

    # Stamp with current version
    if plan.get("schema_version") != CURRENT_SCHEMA_VERSION:
        plan["schema_version"] = CURRENT_SCHEMA_VERSION
        modified = True

    if modified:
        logger.info(
            "Migrated plan '%s' from schema version %s to %s",
            plan.get("name", "unnamed"),
            initial_version,
            CURRENT_SCHEMA_VERSION,
        )

    return plan, modified


def _migrate_v1_to_v2(plan: dict[str, Any]) -> dict[str, Any]:
    """Migrate schema version 1 to 2.

    Changes in v2:
    - Floors support 'shapes' (walls, rooms, openings, labels)
    - Floors support 'sub_areas' (nested room zones with parent_area_id)
    - Endpoints support 'parent_id' (nested entities)
    - Endpoints support 'group_id' and 'group_name' (unified units)
    - Endpoints support 'stale_after' (RF sensor offline tracking)
    """
    # Overview floor
    overview = plan.setdefault("overview", {})
    _ensure_floor_defaults(overview)

    # Buildings & floors
    buildings = plan.setdefault("buildings", [])
    for building in buildings:
        for floor in building.get("floors", []):
            _ensure_floor_defaults(floor)

    return plan


def _ensure_floor_defaults(floor: dict[str, Any]) -> None:
    """Ensure floor object has all required v2 attributes and defaults."""
    floor.setdefault("shapes", [])
    floor.setdefault("sub_areas", [])

    endpoints = floor.get("endpoints", [])
    for ep in endpoints:
        ep.setdefault("parent_id", None)
        ep.setdefault("group_id", None)
        ep.setdefault("group_name", None)
        ep.setdefault("stale_after", None)
        ep.setdefault("companions", [])
        ep.setdefault("cameras", [])
        ep.setdefault("coverage", None)
        ep.setdefault("rotation", 0)
