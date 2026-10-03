"""Tests for live StateManager."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from live.state_manager import StateManager


@pytest.mark.asyncio
async def test_placed_entities_filtering() -> None:
    sm = StateManager()
    sm.load_placed_entities("plan_abc", {"binary_sensor.front_door", "binary_sensor.motion"})

    mock_channel_layer = AsyncMock()

    with patch.object(sm, "_channel_layer", mock_channel_layer):
        # 1. State change for tracked entity
        await sm.on_state_changed(
            {
                "entity_id": "binary_sensor.front_door",
                "new_state": {
                    "state": "on",
                    "attributes": {},
                    "last_changed": "2026-10-03T12:00:00Z",
                },
                "old_state": {"state": "off"},
            }
        )

        mock_channel_layer.group_send.assert_called_once()
        group_call = mock_channel_layer.group_send.call_args
        assert group_call[0][0] == "plan_plan_abc"
        assert group_call[0][1]["entity_id"] == "binary_sensor.front_door"
        assert group_call[0][1]["new_state"]["state"] == "on"

        # 2. State change for untracked entity
        mock_channel_layer.reset_mock()
        await sm.on_state_changed(
            {
                "entity_id": "sensor.weather_temp",
                "new_state": {"state": "72"},
                "old_state": {"state": "71"},
            }
        )
        mock_channel_layer.group_send.assert_not_called()
