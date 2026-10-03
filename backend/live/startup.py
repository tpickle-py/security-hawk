"""Application startup hooks — launches background tasks like HA WebSocket listener."""

from __future__ import annotations

import asyncio
import logging
import os
import threading

logger = logging.getLogger(__name__)

_started = False
_lock = threading.Lock()


def start_ha_listener() -> None:
    """Initialize and start the background Home Assistant WebSocket connection and registry refresh."""
    global _started
    with _lock:
        if _started:
            return
        _started = True

    token = os.environ.get("SUPERVISOR_TOKEN")
    if not token:
        logger.warning("SUPERVISOR_TOKEN not set; skipping Home Assistant background listener.")
        return

    def _run_background() -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        from ha.client import HAWebSocketClient
        from ha.registry import entity_registry
        from live.state_manager import state_manager

        client = HAWebSocketClient(on_state_changed=state_manager.on_state_changed)

        async def _main() -> None:
            # First, attempt an initial entity registry refresh
            try:
                await entity_registry.refresh()
            except Exception as e:
                logger.warning(
                    "Initial entity registry refresh failed (will retry if WS connects): %s", e
                )

            # Start persistent WS connection loop
            await client._run_connection()

        # Run loop with retry on unhandled exceptions
        while True:
            try:
                loop.run_until_complete(_main())
            except Exception as e:
                logger.error("HA background listener error: %s. Reconnecting in 5 seconds...", e)
                try:
                    loop.run_until_complete(asyncio.sleep(5))
                except Exception:
                    break

    thread = threading.Thread(target=_run_background, name="ha-listener-thread", daemon=True)
    thread.start()
    logger.info("Spawned HA background listener thread.")
