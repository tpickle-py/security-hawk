"""Django Channels WebSocket consumer for live state updates.

Browser clients (Editor, Live view, and Kiosk) connect to /ws/live/<plan_id>/
to receive real-time state changes for entities placed on the plan.
"""

from __future__ import annotations

import logging
from typing import Any

from channels.generic.websocket import AsyncJsonWebsocketConsumer

from live.state_manager import state_manager

logger = logging.getLogger(__name__)


class LiveStateConsumer(AsyncJsonWebsocketConsumer):
    """Consumer delivering live HA states to browser clients."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.plan_id: str = "default"
        self.group_name: str = "plan_default"

    async def connect(self) -> None:
        self.plan_id = self.scope["url_route"]["kwargs"].get("plan_id", "default")
        self.group_name = f"plan_{self.plan_id}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        logger.info("Client connected to WS live stream for plan %s", self.plan_id)

        # Send initial states for all placed entities on this plan
        initial = await state_manager.get_placed_states(self.plan_id)
        await self.send_json(
            {
                "type": "initial_states",
                "plan_id": self.plan_id,
                "states": initial,
            }
        )

    async def disconnect(self, close_code: int) -> None:
        logger.info(
            "Client disconnected from WS live stream for plan %s (code %d)",
            self.plan_id,
            close_code,
        )
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content: dict[str, Any], **kwargs: Any) -> None:
        """Handle incoming messages from browser clients."""
        msg_type = content.get("type")
        if msg_type == "ping":
            await self.send_json({"type": "pong"})
        elif msg_type == "refresh_states":
            states = await state_manager.get_placed_states(self.plan_id)
            await self.send_json(
                {
                    "type": "initial_states",
                    "plan_id": self.plan_id,
                    "states": states,
                }
            )

    async def state_update(self, event: dict[str, Any]) -> None:
        """Handler for group messages sent by StateManager."""
        await self.send_json(
            {
                "type": "state_changed",
                "entity_id": event["entity_id"],
                "new_state": event.get("new_state"),
                "old_state": event.get("old_state"),
            }
        )
