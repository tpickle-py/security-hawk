"""Entity registry cache — fetches from HA and provides search/lookup.

Uses the `config/entity_registry/list_for_display` WebSocket command
for a compact entity list, and `get_states` for current state data.
The two are merged to provide a unified view for the entity picker.
"""

from __future__ import annotations

import json
import logging
import os

import websockets

logger = logging.getLogger(__name__)

SUPERVISOR_TOKEN = os.environ.get("SUPERVISOR_TOKEN", "")
WS_URL = os.environ.get("HA_WS_URL", "ws://supervisor/core/websocket")

# Abbreviated keys from HA WebSocket API → human-readable names
KEY_MAP = {
    "ei": "entity_id",
    "pl": "platform",
    "ai": "area_id",
    "di": "device_id",
    "en": "name",
    "ic": "icon",
    "ec": "entity_category",
    "hb": "hidden_by",
    "hn": "has_entity_name",
    "tk": "translation_key",
    "lb": "labels",
}


class EntityRegistry:
    """In-memory cache of HA entity registry data, areas, and current states.

    Call refresh() to populate from HA. After that, search() and
    get_entity()/get_state() provide fast lookups without HA round-trips.
    """

    def __init__(self):
        self._entities: dict[str, dict] = {}
        self._states: dict[str, dict] = {}
        self._areas: dict[str, dict] = {}

    async def refresh(self) -> None:
        """Fetch the full entity registry, area registry, and current states from HA."""
        logger.info("Refreshing entity registry from HA...")

        async with websockets.connect(WS_URL) as ws:
            # Auth
            await ws.recv()  # auth_required
            await ws.send(
                json.dumps(
                    {
                        "type": "auth",
                        "access_token": SUPERVISOR_TOKEN,
                    }
                )
            )
            auth_resp = json.loads(await ws.recv())
            if auth_resp["type"] != "auth_ok":
                raise RuntimeError(f"Auth failed: {auth_resp}")

            # 1. Get entity registry (compact format)
            await ws.send(
                json.dumps(
                    {
                        "id": 1,
                        "type": "config/entity_registry/list_for_display",
                    }
                )
            )
            resp = json.loads(await ws.recv())
            raw_entities = resp.get("result", {}).get("entities", [])

            self._entities = {}
            for raw in raw_entities:
                entity = {KEY_MAP.get(k, k): v for k, v in raw.items()}
                self._entities[entity["entity_id"]] = entity

            # 2. Get current states
            await ws.send(
                json.dumps(
                    {
                        "id": 2,
                        "type": "get_states",
                    }
                )
            )
            resp = json.loads(await ws.recv())
            self._states = {}
            for state in resp.get("result", []):
                self._states[state["entity_id"]] = state

            # 3. Get area registry
            await ws.send(
                json.dumps(
                    {
                        "id": 3,
                        "type": "config/area_registry/list",
                    }
                )
            )
            resp_areas = json.loads(await ws.recv())
            self._areas = {}
            if resp_areas.get("success", False) and "result" in resp_areas:
                for a in resp_areas["result"]:
                    self._areas[a["area_id"]] = a

        logger.info(
            "Loaded %d entities, %d states, %d areas",
            len(self._entities),
            len(self._states),
            len(self._areas),
        )

    def get_areas(self) -> list[dict]:
        """Return list of all registered Home Assistant areas/rooms."""
        return list(self._areas.values())

    def get_area(self, area_id: str) -> dict | None:
        """Get area by ID."""
        return self._areas.get(area_id)

    def get_entity(self, entity_id: str) -> dict | None:
        """Get registry data for an entity."""
        return self._entities.get(entity_id)

    def get_state(self, entity_id: str) -> dict | None:
        """Get the cached state for an entity."""
        return self._states.get(entity_id)

    def update_state(self, entity_id: str, new_state: dict) -> None:
        """Update the cached state for an entity (called on state_changed)."""
        self._states[entity_id] = new_state

    def set_entity_area(self, entity_id: str, area_id: str | None) -> bool:
        """Designate an area for an entity in the local registry."""
        if entity_id in self._entities:
            self._entities[entity_id]["area_id"] = area_id
            return True
        return False

    def lookup_by_friendly_name(self, name: str) -> dict | None:
        """Look up entity by exact or case-insensitive friendly name."""
        name_lower = name.strip().lower()
        for eid, entity in self._entities.items():
            state = self._states.get(eid, {})
            friendly = state.get("attributes", {}).get("friendly_name") or entity.get("name") or eid
            if friendly.strip().lower() == name_lower:
                area = self._areas.get(entity.get("area_id") or "")
                return {
                    "entity_id": eid,
                    "name": friendly,
                    "friendly_name": friendly,
                    "area_id": entity.get("area_id"),
                    "area_name": area.get("name") if area else None,
                    "state": state.get("state"),
                }
        return None

    def search(
        self,
        query: str = "",
        domain: str = "",
        limit: int = 50,
        area_id: str = "",
        unassigned_only: bool = False,
    ) -> list[dict]:
        """Search entities by friendly name, entity_id, or area, with filtering options.

        Returns merged entity + state data for the entity picker UI.
        """
        results = []
        query_lower = query.lower()

        for eid, entity in self._entities.items():
            ent_area_id = entity.get("area_id")
            area = self._areas.get(ent_area_id or "")
            area_name = area.get("name") if area else None

            # Filter unassigned only
            if unassigned_only and ent_area_id:
                continue

            # Filter specific area
            if area_id and ent_area_id != area_id:
                continue

            # State and friendly name
            state = self._states.get(eid, {})
            attributes = state.get("attributes", {})
            friendly_name = attributes.get("friendly_name") or entity.get("name") or eid
            reg_name = entity.get("name", "") or ""
            device_class = (attributes.get("device_class") or entity.get("device_class") or "").lower()

            # Domain / category filter
            if domain:
                fn_lower = friendly_name.lower()
                eid_lower = eid.lower()
                if domain == "motion":
                    is_motion = (
                        (eid.startswith("binary_sensor.") and device_class in ("motion", "occupancy", "presence"))
                        or "motion" in eid_lower
                        or "motion" in fn_lower
                        or "occupancy" in fn_lower
                    )
                    if not is_motion:
                        continue
                elif domain == "door":
                    is_door = (
                        (eid.startswith("binary_sensor.") and device_class in ("door", "garage_door", "opening"))
                        or "door" in eid_lower
                        or "door" in fn_lower
                        or "garage" in eid_lower
                    )
                    if not is_door:
                        continue
                elif domain == "window":
                    is_window = (
                        (eid.startswith("binary_sensor.") and device_class == "window")
                        or "window" in eid_lower
                        or "window" in fn_lower
                    )
                    if not is_window:
                        continue
                elif not eid.startswith(f"{domain}."):
                    continue

            # Skip hidden entities
            if entity.get("hidden_by"):
                continue

            # Text search (searches friendly_name, entity_id, and area_name)
            if query_lower:
                matches_friendly = query_lower in friendly_name.lower()
                matches_eid = query_lower in eid.lower()
                matches_reg_name = query_lower in reg_name.lower()
                matches_area = area_name and query_lower in area_name.lower()
                if not (matches_friendly or matches_eid or matches_reg_name or matches_area):
                    continue

            results.append(
                {
                    "entity_id": eid,
                    "name": friendly_name,
                    "domain": eid.split(".")[0] if "." in eid else "",
                    "device_id": entity.get("device_id"),
                    "area_id": ent_area_id,
                    "area_name": area_name,
                    "icon": entity.get("icon"),
                    "platform": entity.get("platform"),
                    "state": state.get("state"),
                    "device_class": attributes.get("device_class"),
                    "friendly_name": friendly_name,
                }
            )

            if len(results) >= limit:
                break

        return results

    def check_missing(self, entity_ids: set[str]) -> list[str]:
        """Return entity IDs that are not found in the registry (stale endpoints)."""
        return [eid for eid in entity_ids if eid not in self._entities and eid not in self._states]

    def get_all_entity_ids(self) -> list[str]:
        """Return list of all known entity IDs from entities and states."""
        return sorted(list(set(self._entities.keys()) | set(self._states.keys())))


# Module-level singleton
entity_registry = EntityRegistry()
