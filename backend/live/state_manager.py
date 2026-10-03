"""State manager — tracks placed entities per plan and broadcasts filtered state updates.

Listens to state_changed events from Home Assistant Core and only relays updates
for entities that are currently placed on an active plan.
"""

from __future__ import annotations

import logging
from typing import Any

from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)


class StateManager:
    """Maintains placed entity sets per plan and relays matching state changes."""

    def __init__(self) -> None:
        self._placed_entities: dict[str, set[str]] = {}
        self._channel_layer: Any = None

    @property
    def channel_layer(self) -> Any:
        if self._channel_layer is None:
            self._channel_layer = get_channel_layer()
        return self._channel_layer

    def load_placed_entities(self, plan_id: str, entity_ids: set[str]) -> None:
        """Register the set of entity IDs placed on a plan."""
        self._placed_entities[plan_id] = set(entity_ids)
        logger.info("Plan %s: tracking %d placed entities", plan_id, len(entity_ids))

    def get_placed_entity_ids(self, plan_id: str) -> set[str]:
        """Return the set of entity IDs tracked for a plan."""
        if plan_id not in self._placed_entities:
            # Attempt to populate from plan storage
            from plans.views import get_storage

            plan = get_storage().load(plan_id)
            if plan:
                from plans.views import _update_placed_entities

                _update_placed_entities(plan_id, plan)
        return self._placed_entities.get(plan_id, set())

    async def on_state_changed(self, event_data: dict[str, Any]) -> None:
        """Process a state_changed event from HA."""
        entity_id = event_data.get("entity_id")
        if not entity_id:
            return

        new_state = event_data.get("new_state")
        old_state = event_data.get("old_state")

        # Update entity registry state cache
        from ha.registry import entity_registry

        if new_state:
            entity_registry.update_state(entity_id, new_state)

        # Broadcast to any plan containing this entity
        channel_layer = self.channel_layer
        if not channel_layer:
            return

        for plan_id, entities in list(self._placed_entities.items()):
            if entity_id in entities:
                await channel_layer.group_send(
                    f"plan_{plan_id}",
                    {
                        "type": "state_update",
                        "entity_id": entity_id,
                        "new_state": new_state,
                        "old_state": old_state,
                    },
                )

        # Evaluate correlated rules and publish synthetic sensors
        try:
            from rules.engine import rules_engine

            await rules_engine.process_state_change(entity_id, new_state)
        except Exception as e:
            logger.debug("Rules evaluation failed for entity %s: %s", entity_id, e)

    async def get_placed_states(self, plan_id: str) -> dict[str, Any]:
        """Return current states for all placed entities on a plan."""
        from ha.registry import entity_registry

        entities = self.get_placed_entity_ids(plan_id)
        states: dict[str, Any] = {}
        for eid in entities:
            st = entity_registry.get_state(eid)
            if st is not None:
                states[eid] = {
                    "entity_id": eid,
                    "state": st.get("state"),
                    "attributes": st.get("attributes", {}),
                    "last_changed": st.get("last_changed"),
                }
        return states


state_manager = StateManager()
