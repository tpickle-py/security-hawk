"""Correlated Compound Rules Engine.

Evaluates multi-condition ('If X, Y, Z Then X') logic, time-window correlations,
and publishes synthetic sensor states to Home Assistant Core REST API & MQTT.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from channels.layers import get_channel_layer

from ha.client import HARestClient
from ha.mqtt import LightweightMqttClient
from ha.registry import entity_registry
from rules.storage import rules_storage
from settings_mgr.storage import settings_storage

logger = logging.getLogger(__name__)


class RulesEngine:
    """Evaluates rules against incoming state changes and executes actions."""

    def __init__(self) -> None:
        self._recent_events: dict[str, dict[str, Any]] = {}
        self._reset_tasks: dict[str, asyncio.Task] = {}
        self._ha_client = HARestClient()

    def record_event(self, entity_id: str, state: str) -> None:
        """Record state event with monotonic timestamp for time correlation."""
        self._recent_events[entity_id] = {
            "state": state.lower(),
            "time": time.time(),
        }

    async def process_state_change(self, entity_id: str, new_state: dict[str, Any] | None) -> None:
        """Process an incoming state change from HA WebSocket."""
        if not new_state:
            return

        state_val = str(new_state.get("state", "")).lower()
        self.record_event(entity_id, state_val)

        rules = rules_storage.list_rules()
        for rule in rules:
            if not rule.get("enabled", True):
                continue

            # Check if this entity is part of rule's conditions
            conditions = rule.get("conditions", [])
            relevant = any(c.get("entity_id") == entity_id for c in conditions)
            if not relevant:
                continue

            triggered, matched_entities = self.evaluate_rule(rule)
            if triggered:
                await self.execute_rule(rule, matched_entities)

    def evaluate_rule(self, rule: dict[str, Any]) -> tuple[bool, list[str]]:
        """Evaluate conditions for a rule considering time-window correlation."""
        conditions = rule.get("conditions", [])
        if not conditions:
            return False, []

        logic = rule.get("logic", "ALL").upper()
        time_window = float(rule.get("time_window_seconds", 30))
        now = time.time()

        matched_entities: list[str] = []
        condition_results: list[bool] = []

        for cond in conditions:
            eid = cond.get("entity_id")
            target_state = str(cond.get("state", "on")).lower()
            if not eid:
                continue

            # Check current registry state first
            current_st = entity_registry.get_state(eid)
            current_val = str(current_st.get("state", "")).lower() if current_st else ""

            # Check recent events within window
            recent = self._recent_events.get(eid)
            is_matched = False

            if current_val == target_state or (
                recent and (now - recent["time"]) <= time_window and recent["state"] == target_state
            ):
                is_matched = True

            if is_matched:
                matched_entities.append(eid)
                condition_results.append(True)
            else:
                condition_results.append(False)

        if logic == "ALL":
            return all(condition_results) and len(condition_results) > 0, matched_entities
        else:  # ANY
            return any(condition_results), matched_entities

    async def execute_rule(self, rule: dict[str, Any], triggering_entities: list[str]) -> None:
        """Execute actions: publish to HA, MQTT, optional service call, and notify UI."""
        rule_id = rule["id"]
        output_eid = rule.get("output_entity_id") or f"binary_sensor.security_hawk_{rule_id}"
        rule_name = rule.get("name", "Correlated Rule")
        device_class = rule.get("device_class", "safety")
        reset_seconds = int(rule.get("reset_seconds", 60))

        logger.info("Rule triggered: '%s' by %s", rule_name, triggering_entities)

        # 1. Publish synthetic state to Home Assistant Core REST API
        attributes = {
            "friendly_name": f"Security Hawk {rule_name}",
            "device_class": device_class,
            "triggered_by": triggering_entities,
            "rule_id": rule_id,
            "icon": "mdi:shield-alert",
        }
        try:
            await self._ha_client.set_state(output_eid, "on", attributes)
        except Exception as e:
            logger.warning("Failed to publish synthetic state to HA: %s", e)

        # 2. Publish to MQTT if enabled
        app_settings = settings_storage.load()
        mqtt_cfg = app_settings.get("mqtt", {})
        if mqtt_cfg.get("enabled"):
            try:
                mqtt = LightweightMqttClient(
                    host=mqtt_cfg.get("host", "localhost"),
                    port=int(mqtt_cfg.get("port", 1883)),
                    username=mqtt_cfg.get("username", ""),
                    password=mqtt_cfg.get("password", ""),
                )
                topic_prefix = mqtt_cfg.get("topic_prefix", "security_hawk/")
                state_topic = f"{topic_prefix}sensor/{rule_id}/state"

                # Publish discovery if configured
                if mqtt_cfg.get("ha_discovery", True):
                    await mqtt.publish_ha_discovery(rule_id, rule_name, state_topic, device_class)

                # Publish state
                await mqtt.publish(state_topic, "ON", retain=True)
            except Exception as e:
                logger.debug("Failed to publish MQTT state: %s", e)

        # 3. Optional HA service call (e.g. alarm trigger or siren)
        svc = rule.get("service_call")
        if svc and isinstance(svc, dict) and svc.get("domain") and svc.get("service"):
            try:
                await self._ha_client.call_service(
                    domain=svc["domain"],
                    service=svc["service"],
                    service_data=svc.get("data", {}),
                )
            except Exception as e:
                logger.warning("Failed to call service for rule '%s': %s", rule_name, e)

        # 4. Broadcast state update to connected frontend floor plans
        channel_layer = get_channel_layer()
        if channel_layer:
            await channel_layer.group_send(
                "security_hawk_broadcast",
                {
                    "type": "state_update",
                    "entity_id": output_eid,
                    "new_state": {
                        "state": "on",
                        "attributes": attributes,
                        "last_changed": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    },
                },
            )

        # 5. Schedule auto-reset back to OFF
        if rule_id in self._reset_tasks:
            self._reset_tasks[rule_id].cancel()

        loop = asyncio.get_event_loop()
        self._reset_tasks[rule_id] = loop.create_task(
            self._schedule_reset(output_eid, rule_id, reset_seconds, attributes)
        )

    async def _schedule_reset(
        self, output_eid: str, rule_id: str, delay_seconds: int, base_attributes: dict[str, Any]
    ) -> None:
        """Reset the synthetic entity to 'off' after the delay."""
        try:
            await asyncio.sleep(delay_seconds)
            off_attributes = dict(base_attributes)
            off_attributes["triggered_by"] = []
            off_attributes["icon"] = "mdi:shield-check"

            # 1. Reset HA state
            try:
                await self._ha_client.set_state(output_eid, "off", off_attributes)
            except Exception as e:
                logger.debug("Failed to reset HA synthetic state to off: %s", e)

            # 2. Reset MQTT if enabled
            app_settings = settings_storage.load()
            mqtt_cfg = app_settings.get("mqtt", {})
            if mqtt_cfg.get("enabled"):
                try:
                    mqtt = LightweightMqttClient(
                        host=mqtt_cfg.get("host", "localhost"),
                        port=int(mqtt_cfg.get("port", 1883)),
                        username=mqtt_cfg.get("username", ""),
                        password=mqtt_cfg.get("password", ""),
                    )
                    topic_prefix = mqtt_cfg.get("topic_prefix", "security_hawk/")
                    state_topic = f"{topic_prefix}sensor/{rule_id}/state"
                    await mqtt.publish(state_topic, "OFF", retain=True)
                except Exception as e:
                    logger.debug("Failed to reset MQTT state: %s", e)

            # 3. Broadcast reset to frontend
            channel_layer = get_channel_layer()
            if channel_layer:
                await channel_layer.group_send(
                    "security_hawk_broadcast",
                    {
                        "type": "state_update",
                        "entity_id": output_eid,
                        "new_state": {
                            "state": "off",
                            "attributes": off_attributes,
                            "last_changed": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        },
                    },
                )
        except asyncio.CancelledError:
            pass
        finally:
            self._reset_tasks.pop(rule_id, None)


rules_engine = RulesEngine()
