"""Home Assistant API clients — REST for one-shot queries, WebSocket for live events.

The REST client fetches entity states and proxies camera snapshots.
The WebSocket client maintains a persistent connection to HA Core,
subscribing to state_changed events and forwarding them to the state manager.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os

import aiohttp
import websockets

logger = logging.getLogger(__name__)

SUPERVISOR_URL = os.environ.get("SUPERVISOR_URL", "http://supervisor")
SUPERVISOR_TOKEN = os.environ.get("SUPERVISOR_TOKEN", "")
WS_URL = os.environ.get("HA_WS_URL", "ws://supervisor/core/websocket")


class HARestClient:
    """Synchronous-friendly REST client for the HA Core API via Supervisor proxy."""

    def __init__(self):
        self.base_url = f"{SUPERVISOR_URL}/core/api"
        self.headers = {
            "Authorization": f"Bearer {SUPERVISOR_TOKEN}",
            "Content-Type": "application/json",
        }

    async def get_states(self) -> list[dict]:
        """Fetch all current entity states."""
        async with (
            aiohttp.ClientSession() as session,
            session.get(
                f"{self.base_url}/states",
                headers=self.headers,
            ) as resp,
        ):
            resp.raise_for_status()
            return await resp.json()

    async def get_state(self, entity_id: str) -> dict | None:
        """Fetch a single entity's state."""
        async with (
            aiohttp.ClientSession() as session,
            session.get(
                f"{self.base_url}/states/{entity_id}",
                headers=self.headers,
            ) as resp,
        ):
            if resp.status == 404:
                return None
            resp.raise_for_status()
            return await resp.json()

    async def get_camera_snapshot(self, entity_id: str) -> tuple[bytes, str]:
        """Fetch a camera snapshot image. Returns (image_bytes, content_type)."""
        async with (
            aiohttp.ClientSession() as session,
            session.get(
                f"{self.base_url}/camera_proxy/{entity_id}",
                headers=self.headers,
            ) as resp,
        ):
            resp.raise_for_status()
            content_type = resp.content_type or "image/jpeg"
            return await resp.read(), content_type

    async def set_state(self, entity_id: str, state: str, attributes: dict | None = None) -> dict:
        """Publish or update an entity state directly into Home Assistant Core.

        Uses the HA REST API POST /api/states/<entity_id> endpoint.
        If the entity does not exist, Home Assistant registers it dynamically.
        """
        payload = {"state": state, "attributes": attributes or {}}
        async with (
            aiohttp.ClientSession() as session,
            session.post(
                f"{self.base_url}/states/{entity_id}",
                headers=self.headers,
                json=payload,
            ) as resp,
        ):
            resp.raise_for_status()
            return await resp.json()

    async def call_service(
        self, domain: str, service: str, service_data: dict | None = None
    ) -> list[dict]:
        """Call a Home Assistant service (e.g. alarm_control_panel.alarm_trigger)."""
        payload = service_data or {}
        async with (
            aiohttp.ClientSession() as session,
            session.post(
                f"{self.base_url}/services/{domain}/{service}",
                headers=self.headers,
                json=payload,
            ) as resp,
        ):
            resp.raise_for_status()
            return await resp.json()


class HAWebSocketClient:
    """Persistent WebSocket connection to HA Core for live state events.

    Connects via the Supervisor proxy at ws://supervisor/core/websocket,
    authenticates with SUPERVISOR_TOKEN, and subscribes to state_changed events.
    Auto-reconnects with exponential backoff on connection loss.
    """

    def __init__(self, on_state_changed):
        self.on_state_changed = on_state_changed
        self._ws = None
        self._msg_id = 0
        self._running = False
        self._task: asyncio.Task | None = None

    def _next_id(self) -> int:
        self._msg_id += 1
        return self._msg_id

    def start(self) -> None:
        """Start the WebSocket listener in the background event loop."""
        if self._running:
            return
        self._running = True

        loop = asyncio.get_event_loop()
        self._task = loop.create_task(self._connect_loop())
        logger.info("HA WebSocket listener started")

    async def stop(self) -> None:
        """Gracefully stop the WebSocket listener."""
        self._running = False
        if self._ws:
            await self._ws.close()
        if self._task:
            self._task.cancel()

    async def _connect_loop(self) -> None:
        """Reconnect loop with exponential backoff."""
        backoff = 1.0
        while self._running:
            try:
                await self._run_connection()
            except Exception as e:
                logger.error("HA WS connection error: %s — reconnecting in %.0fs", e, backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30.0)
            else:
                backoff = 1.0  # Reset on clean disconnect

    async def _run_connection(self) -> None:
        """Single connection lifecycle: auth → subscribe → listen."""
        logger.info("Connecting to HA WebSocket at %s", WS_URL)

        async with websockets.connect(WS_URL) as ws:
            self._ws = ws

            # Authentication phase
            msg = json.loads(await ws.recv())
            if msg["type"] != "auth_required":
                raise RuntimeError(f"Unexpected message: {msg}")

            await ws.send(
                json.dumps(
                    {
                        "type": "auth",
                        "access_token": SUPERVISOR_TOKEN,
                    }
                )
            )

            msg = json.loads(await ws.recv())
            if msg["type"] != "auth_ok":
                raise RuntimeError(f"Authentication failed: {msg}")

            logger.info("Authenticated with HA Core (version %s)", msg.get("ha_version"))

            # Subscribe to state_changed events
            sub_id = self._next_id()
            await ws.send(
                json.dumps(
                    {
                        "id": sub_id,
                        "type": "subscribe_events",
                        "event_type": "state_changed",
                    }
                )
            )
            ack = json.loads(await ws.recv())
            if not ack.get("success"):
                raise RuntimeError(f"Subscribe failed: {ack}")

            logger.info("Subscribed to state_changed events (sub_id=%d)", sub_id)

            # Listen for events
            async for raw in ws:
                if not self._running:
                    break
                msg = json.loads(raw)
                if msg.get("type") == "event" and msg.get("id") == sub_id:
                    event_data = msg["event"]["data"]
                    try:
                        await self.on_state_changed(event_data)
                    except Exception:
                        logger.exception("Error handling state_changed event")
