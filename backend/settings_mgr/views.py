"""Views for app settings, MQTT configuration, and HA helper registrations."""

from __future__ import annotations

import json

from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from ha.client import HARestClient
from ha.mqtt import LightweightMqttClient
from rules.storage import rules_storage
from settings_mgr.storage import settings_storage


@csrf_exempt
def get_or_update_settings(request: HttpRequest) -> JsonResponse:
    """GET /api/settings/ or POST /api/settings/"""
    if request.method == "GET":
        data = settings_storage.load()
        return JsonResponse({"settings": data})

    if request.method == "POST":
        try:
            body = json.loads(request.body.decode("utf-8"))
        except Exception:
            return JsonResponse({"error": "Invalid JSON body"}, status=400)

        saved = settings_storage.save(body)
        return JsonResponse({"status": "ok", "settings": saved})

    return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
async def register_ha_helpers(request: HttpRequest) -> JsonResponse:
    """POST /api/settings/register_ha_helpers/

    Iterates over all defined rules and default synthetic entities,
    and actively pushes initial 'off' states and metadata into Home Assistant Core
    via REST API, plus publishes MQTT discovery payloads if MQTT is enabled.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    rules = rules_storage.list_rules()
    app_settings = settings_storage.load()
    mqtt_cfg = app_settings.get("mqtt", {})
    ha_client = HARestClient()

    results: list[dict] = []

    for rule in rules:
        rule_id = rule["id"]
        output_eid = rule.get("output_entity_id") or f"binary_sensor.security_hawk_{rule_id}"
        rule_name = rule.get("name", "Correlated Rule")
        device_class = rule.get("device_class", "safety")

        # 1. Register in HA REST API
        attrs = {
            "friendly_name": f"Security Hawk {rule_name}",
            "device_class": device_class,
            "rule_id": rule_id,
            "icon": "mdi:shield-check",
            "triggered_by": [],
        }
        ha_status = "registered"
        try:
            await ha_client.set_state(output_eid, "off", attrs)
        except Exception as e:
            ha_status = f"failed: {e}"

        # 2. MQTT Discovery if enabled
        mqtt_status = "disabled"
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
                if mqtt_cfg.get("ha_discovery", True):
                    await mqtt.publish_ha_discovery(rule_id, rule_name, state_topic, device_class)
                await mqtt.publish(state_topic, "OFF", retain=True)
                mqtt_status = "published"
            except Exception as e:
                mqtt_status = f"failed: {e}"

        results.append(
            {
                "rule_id": rule_id,
                "entity_id": output_eid,
                "ha_registration": ha_status,
                "mqtt_discovery": mqtt_status,
            }
        )

    return JsonResponse(
        {
            "status": "ok",
            "registered_count": len(results),
            "count": len(results),
            "entities": results,
            "results": results,
        }
    )
