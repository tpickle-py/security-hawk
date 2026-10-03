"""Dedicated decoupled background worker and event queue for Rules Engine.

Ensures rule matching, time-window evaluation, and external network actions (Discord,
Slack, WhatsApp, Email, Webhooks, Home Assistant services) execute completely decoupled
from the main WebSocket event loop and API request handlers.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class RuleEventWorker:
    """Consumes incoming state changes from an asynchronous queue and evaluates rules."""

    def __init__(self, max_queue_size: int = 1000) -> None:
        self.max_queue_size = max_queue_size
        self._queue: asyncio.Queue[tuple[str, dict[str, Any] | None]] | None = None
        self._worker_task: asyncio.Task[None] | None = None
        self._running = False

        # Metrics & Telemetry
        self._events_enqueued: int = 0
        self._events_processed: int = 0
        self._actions_dispatched: int = 0
        self._last_event_time: float | None = None

    def _ensure_queue(self) -> asyncio.Queue[tuple[str, dict[str, Any] | None]]:
        if self._queue is None:
            self._queue = asyncio.Queue(maxsize=self.max_queue_size)
        return self._queue

    def start(self) -> None:
        """Start the background worker task if not already running."""
        if self._running and self._worker_task and not self._worker_task.done():
            return

        self._ensure_queue()
        self._running = True
        try:
            loop = asyncio.get_running_loop()
            self._worker_task = loop.create_task(self._worker_loop(), name="security_hawk_rule_worker")
            logger.info("Security Hawk decoupled Rule Worker started in background task.")
        except RuntimeError:
            logger.debug("No active asyncio loop available to start Rule Worker yet.")

    def stop(self) -> None:
        """Gracefully stop the background worker task."""
        self._running = False
        if self._worker_task and not self._worker_task.done():
            self._worker_task.cancel()
            logger.info("Security Hawk Rule Worker cancelled.")

    def enqueue(self, entity_id: str, new_state: dict[str, Any] | None) -> bool:
        """Instantly enqueue a state change event without blocking the caller."""
        q = self._ensure_queue()
        # Auto-start if worker loop wasn't started
        if not self._running or self._worker_task is None or self._worker_task.done():
            self.start()

        self._events_enqueued += 1
        self._last_event_time = time.time()
        try:
            q.put_nowait((entity_id, new_state))
            return True
        except asyncio.QueueFull:
            logger.warning("Rule Worker event queue is full (%d items); dropping event for %s", q.qsize(), entity_id)
            return False

    async def _worker_loop(self) -> None:
        """Continuous consumer loop."""
        from rules.engine import rules_engine

        logger.debug("Rule Worker loop active and listening for state events.")
        while self._running:
            try:
                assert self._queue is not None
                entity_id, new_state = await self._queue.get()
                self._events_processed += 1

                try:
                    # Evaluate rules for this state change
                    await rules_engine.process_state_change(entity_id, new_state)
                except Exception as eval_err:
                    logger.error("Error evaluating rules for entity '%s': %s", entity_id, eval_err)
                finally:
                    self._queue.task_done()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Unexpected error in Rule Worker loop: %s", e)
                await asyncio.sleep(0.05)

    def get_stats(self) -> dict[str, Any]:
        """Return runtime queue and worker throughput metrics."""
        q_depth = self._queue.qsize() if self._queue is not None else 0
        return {
            "running": self._running and self._worker_task is not None and not self._worker_task.done(),
            "queue_depth": q_depth,
            "max_queue_size": self.max_queue_size,
            "events_enqueued": self._events_enqueued,
            "events_processed": self._events_processed,
            "actions_dispatched": self._actions_dispatched,
            "last_event_timestamp": self._last_event_time,
        }


rule_worker = RuleEventWorker()
