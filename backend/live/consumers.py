"""Django Channels WebSocket consumer for live state updates.

Browser clients (Editor, Live view, and Kiosk) connect to /ws/live/<plan_id>/
to receive real-time state changes for entities placed on the plan.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from channels.generic.websocket import AsyncJsonWebsocketConsumer

from live.state_manager import state_manager

logger = logging.getLogger(__name__)


class ConnectionTracker:
    """Tracks active WebSocket connections, viewer counts, and kiosk sessions."""

    def __init__(self) -> None:
        self._connections: dict[str, dict[str, Any]] = {}

    def add(self, channel_name: str, plan_id: str, is_kiosk: bool) -> None:
        self._connections[channel_name] = {
            "plan_id": plan_id,
            "is_kiosk": is_kiosk,
            "connected_at": time.time(),
        }

    def remove(self, channel_name: str) -> None:
        self._connections.pop(channel_name, None)

    def get_plan_count(self, plan_id: str) -> int:
        return sum(1 for c in self._connections.values() if c.get("plan_id") == plan_id)

    def get_total_count(self) -> int:
        return len(self._connections)

    def get_stats(self) -> dict[str, Any]:
        total = len(self._connections)
        kiosk_count = sum(1 for c in self._connections.values() if c.get("is_kiosk"))
        by_plan: dict[str, int] = {}
        for c in self._connections.values():
            pid = str(c.get("plan_id", "default"))
            by_plan[pid] = by_plan.get(pid, 0) + 1
        return {
            "total_viewers": total,
            "kiosk_viewers": kiosk_count,
            "standard_viewers": max(0, total - kiosk_count),
            "by_plan": by_plan,
        }


connection_tracker = ConnectionTracker()


class LiveStateConsumer(AsyncJsonWebsocketConsumer):
    """Consumer delivering live HA states to browser clients."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.plan_id: str = "default"
        self.group_name: str = "plan_default"
        self.is_kiosk: bool = False

    async def connect(self) -> None:
        self.plan_id = self.scope["url_route"]["kwargs"].get("plan_id", "default")
        self.group_name = f"plan_{self.plan_id}"

        # Detect whether connecting client is a kiosk display
        query_string = self.scope.get("query_string", b"").decode("utf-8")
        self.is_kiosk = "client=kiosk" in query_string or "kiosk" in query_string

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        connection_tracker.add(self.channel_name, self.plan_id, self.is_kiosk)
        plan_count = connection_tracker.get_plan_count(self.plan_id)
        total_count = connection_tracker.get_total_count()

        logger.info(
            "Client connected to WS live stream for plan %s (kiosk=%s, plan_viewers=%d, total=%d)",
            self.plan_id,
            self.is_kiosk,
            plan_count,
            total_count,
        )

        # Broadcast updated viewer count to other clients viewing this plan
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "viewer_update",
                "count": plan_count,
                "total": total_count,
            },
        )

        # Send initial states for all placed entities on this plan
        initial = await state_manager.get_placed_states(self.plan_id)
        await self.send_json(
            {
                "type": "initial_states",
                "plan_id": self.plan_id,
                "states": initial,
                "viewer_count": plan_count,
                "total_viewers": total_count,
            }
        )

    async def disconnect(self, close_code: int) -> None:
        connection_tracker.remove(self.channel_name)
        plan_count = connection_tracker.get_plan_count(self.plan_id)
        total_count = connection_tracker.get_total_count()

        logger.info(
            "Client disconnected from WS live stream for plan %s (code %d, plan_viewers=%d)",
            self.plan_id,
            close_code,
            plan_count,
        )
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

        # Broadcast updated viewer count to remaining clients
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "viewer_update",
                "count": plan_count,
                "total": total_count,
            },
        )

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
                    "viewer_count": connection_tracker.get_plan_count(self.plan_id),
                    "total_viewers": connection_tracker.get_total_count(),
                }
            )

    async def viewer_update(self, event: dict[str, Any]) -> None:
        """Handler for viewer count broadcast to clients in this plan group."""
        await self.send_json(
            {
                "type": "viewer_count",
                "count": event.get("count", 1),
                "total": event.get("total", 1),
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
