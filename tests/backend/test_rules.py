"""Unit tests for the rules engine, rule storage, and synthetic sensor publishing."""

from __future__ import annotations

import pytest

from rules.engine import RulesEngine
from rules.storage import RulesStorage


@pytest.fixture
def rules_storage_instance(tmp_path):
    return RulesStorage(data_dir=tmp_path)


def test_rules_storage_crud(rules_storage_instance):
    # Empty
    assert rules_storage_instance.list_rules() == []

    # Create rule
    rule_data = {
        "name": "Backyard Perimeter Breach",
        "output_entity_id": "binary_sensor.security_hawk_backyard_breach",
        "logic": "ALL",
        "conditions": [
            {"entity_id": "binary_sensor.backyard_motion", "state": "on"},
            {"entity_id": "camera.backyard", "state": "person"},
        ],
    }
    saved = rules_storage_instance.create_or_update(rule_data)
    assert saved["id"].startswith("rule_")
    assert saved["enabled"] is True
    assert saved["time_window_seconds"] == 30

    # Retrieve
    loaded = rules_storage_instance.get_rule(saved["id"])
    assert loaded is not None
    assert loaded["name"] == "Backyard Perimeter Breach"

    # Update
    saved["name"] = "Updated Perimeter Breach"
    rules_storage_instance.create_or_update(saved)
    updated = rules_storage_instance.get_rule(saved["id"])
    assert updated["name"] == "Updated Perimeter Breach"

    # Delete
    deleted = rules_storage_instance.delete(saved["id"])
    assert deleted is True
    assert rules_storage_instance.get_rule(saved["id"]) is None


def test_rules_engine_evaluation_logic():
    engine = RulesEngine()

    rule_all = {
        "id": "rule_test",
        "name": "Test Rule",
        "logic": "ALL",
        "time_window_seconds": 30,
        "conditions": [
            {"entity_id": "binary_sensor.motion1", "state": "on"},
            {"entity_id": "binary_sensor.motion2", "state": "on"},
        ],
    }

    # Record only one condition
    engine.record_event("binary_sensor.motion1", "on")
    triggered, matched = engine.evaluate_rule(rule_all)
    assert triggered is False

    # Record second condition -> now ALL matches
    engine.record_event("binary_sensor.motion2", "on")
    triggered, matched = engine.evaluate_rule(rule_all)
    assert triggered is True
    assert set(matched) == {"binary_sensor.motion1", "binary_sensor.motion2"}

    # Test ANY logic
    rule_any = {
        "id": "rule_any",
        "name": "Any Rule",
        "logic": "ANY",
        "time_window_seconds": 30,
        "conditions": [
            {"entity_id": "binary_sensor.motion_rare", "state": "on"},
            {"entity_id": "binary_sensor.motion1", "state": "on"},
        ],
    }
    triggered_any, matched_any = engine.evaluate_rule(rule_any)
    assert triggered_any is True
    assert "binary_sensor.motion1" in matched_any


@pytest.mark.asyncio
async def test_rules_api_endpoints(async_client, tmp_path, monkeypatch):
    from rules import storage

    custom_storage = RulesStorage(data_dir=tmp_path)
    monkeypatch.setattr(storage, "rules_storage", custom_storage)
    from rules import views

    monkeypatch.setattr(views, "rules_storage", custom_storage)

    # 1. List rules
    resp = await async_client.get("/api/rules/")
    assert resp.status_code == 200
    assert resp.json()["rules"] == []

    # 2. Create rule
    payload = {
        "name": "Front Porch Package Alert",
        "output_entity_id": "binary_sensor.security_hawk_porch_package",
        "logic": "ALL",
        "conditions": [
            {"entity_id": "camera.front_door", "state": "package"},
        ],
    }
    resp = await async_client.post("/api/rules/", data=payload, content_type="application/json")
    assert resp.status_code == 201
    created_id = resp.json()["rule"]["id"]

    # 3. Get single rule
    resp = await async_client.get(f"/api/rules/{created_id}/")
    assert resp.status_code == 200
    assert resp.json()["rule"]["name"] == "Front Porch Package Alert"

    # 4. Test rule execution endpoint
    resp = await async_client.post(f"/api/rules/{created_id}/test/")
    assert resp.status_code == 200
    assert resp.json()["status"] == "triggered"

    # 5. Delete rule
    resp = await async_client.delete(f"/api/rules/{created_id}/")
    assert resp.status_code == 200
    assert resp.json()["status"] == "deleted"

    # 6. Test 404 on deleted rule
    resp = await async_client.get(f"/api/rules/{created_id}/")
    assert resp.status_code == 404

    resp = await async_client.post(f"/api/rules/{created_id}/test/")
    assert resp.status_code == 404

    # 7. Invalid JSON in POST
    resp = await async_client.post("/api/rules/", data="bad json", content_type="application/json")
    assert resp.status_code == 400


def test_rules_engine_time_window_expiration():
    import time
    engine = RulesEngine()

    rule = {
        "id": "rule_timeout",
        "name": "Timeout Rule",
        "logic": "ALL",
        "time_window_seconds": 1,
        "conditions": [
            {"entity_id": "binary_sensor.a", "state": "on"},
            {"entity_id": "binary_sensor.b", "state": "on"},
        ],
    }

    # Record first event with artificially old timestamp
    engine._recent_events["binary_sensor.a"] = {"state": "on", "time": time.time() - 10}
    engine._recent_events["binary_sensor.b"] = {"state": "on", "time": time.time()}

    triggered, _ = engine.evaluate_rule(rule)
    # binary_sensor.a event is outside 1 second window
    assert triggered is False


def test_mqtt_encoding_and_discovery():
    from ha.mqtt import LightweightMqttClient, _encode_remaining_length, _encode_utf8_str

    # Test variable length encoding
    assert _encode_remaining_length(0) == b"\x00"
    assert _encode_remaining_length(127) == b"\x7f"
    assert _encode_remaining_length(128) == b"\x80\x01"

    # Test UTF-8 string encoding (2-byte prefix + string)
    encoded = _encode_utf8_str("test")
    assert encoded == b"\x00\x04test"

    client = LightweightMqttClient(host="127.0.0.1", port=1883)
    assert client.host == "127.0.0.1"


@pytest.mark.asyncio
async def test_rules_engine_process_state_change(tmp_path, monkeypatch):
    from rules import storage
    custom_storage = RulesStorage(data_dir=tmp_path)
    monkeypatch.setattr(storage, "rules_storage", custom_storage)
    monkeypatch.setattr("rules.engine.rules_storage", custom_storage)

    custom_storage.create_or_update({
        "name": "Live Correlation Rule",
        "output_entity_id": "binary_sensor.security_hawk_live_corr",
        "logic": "ALL",
        "time_window_seconds": 10,
        "reset_seconds": 5,
        "conditions": [
            {"entity_id": "binary_sensor.door_contact", "state": "on"},
        ],
    })

    engine = RulesEngine()
    # Mock HA client set_state to verify trigger
    ha_calls = []
    async def mock_set_state(entity_id, state, attributes=None):
        ha_calls.append((entity_id, state, attributes))
        return {"state": state}

    monkeypatch.setattr(engine._ha_client, "set_state", mock_set_state)

    # Process state change that triggers the rule
    await engine.process_state_change("binary_sensor.door_contact", {"state": "on"})
    assert len(ha_calls) >= 1
    assert ha_calls[0][0] == "binary_sensor.security_hawk_live_corr"
    assert ha_calls[0][1] == "on"
