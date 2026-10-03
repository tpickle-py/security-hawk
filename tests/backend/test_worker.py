"""Unit tests for RuleEventWorker (decoupled background rule execution)."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from rules.worker import RuleEventWorker


@pytest.mark.asyncio
async def test_rule_worker_enqueue_and_process():
    worker = RuleEventWorker(max_queue_size=10)

    with patch("rules.engine.rules_engine.process_state_change", new_callable=AsyncMock) as mock_process:
        # Enqueue state changes
        success1 = worker.enqueue("binary_sensor.front_motion", {"state": "on"})
        success2 = worker.enqueue("camera.front_door", {"state": "idle"})

        assert success1 is True
        assert success2 is True

        # Wait for worker loop to consume events
        await asyncio.sleep(0.05)

        assert mock_process.call_count == 2
        mock_process.assert_any_call("binary_sensor.front_motion", {"state": "on"})
        mock_process.assert_any_call("camera.front_door", {"state": "idle"})

        stats = worker.get_stats()
        assert stats["events_enqueued"] == 2
        assert stats["events_processed"] == 2
        assert stats["running"] is True

        worker.stop()
        assert worker._running is False


@pytest.mark.asyncio
async def test_rule_worker_queue_full():
    worker = RuleEventWorker(max_queue_size=2)
    # Don't start worker loop yet to simulate queue backlog
    worker._running = True  # trick it into thinking it's running so start() doesn't spawn task yet
    worker._ensure_queue()

    # Fill queue to capacity
    res1 = worker.enqueue("sensor.1", {"state": "1"})
    res2 = worker.enqueue("sensor.2", {"state": "2"})
    # Third should drop gracefully
    res3 = worker.enqueue("sensor.3", {"state": "3"})

    assert res1 is True
    assert res2 is True
    assert res3 is False  # queue full

    worker.stop()
