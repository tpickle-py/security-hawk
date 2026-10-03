"""Unit tests for EntityRegistry search, areas, and friendly name lookup."""

from __future__ import annotations

from ha.registry import EntityRegistry


def test_entity_registry_search_and_areas() -> None:
    reg = EntityRegistry()

    # Seed data
    reg._areas = {
        "kitchen": {"area_id": "kitchen", "name": "Kitchen"},
        "living_room": {"area_id": "living_room", "name": "Living Room"},
    }

    reg._entities = {
        "binary_sensor.front_motion": {
            "entity_id": "binary_sensor.front_motion",
            "name": "Front Porch Motion",
            "area_id": None,
            "device_id": "dev_1",
        },
        "binary_sensor.kitchen_door": {
            "entity_id": "binary_sensor.kitchen_door",
            "name": "Back Door",
            "area_id": "kitchen",
            "device_id": "dev_2",
        },
        "camera.driveway": {
            "entity_id": "camera.driveway",
            "name": "Driveway Cam",
            "area_id": "living_room",
            "device_id": "dev_3",
        },
    }

    reg._states = {
        "binary_sensor.front_motion": {
            "entity_id": "binary_sensor.front_motion",
            "state": "on",
            "attributes": {"friendly_name": "Front Porch Motion Sensor"},
        },
        "binary_sensor.kitchen_door": {
            "entity_id": "binary_sensor.kitchen_door",
            "state": "off",
            "attributes": {"friendly_name": "Kitchen Back Door"},
        },
        "camera.driveway": {
            "entity_id": "camera.driveway",
            "state": "idle",
            "attributes": {"friendly_name": "Driveway Security Camera"},
        },
    }

    # 1. Search by friendly name
    res = reg.search(query="Security Camera")
    assert len(res) == 1
    assert res[0]["entity_id"] == "camera.driveway"

    # 2. Search unassigned only
    res_unassigned = reg.search(unassigned_only=True)
    assert len(res_unassigned) == 1
    assert res_unassigned[0]["entity_id"] == "binary_sensor.front_motion"
    assert res_unassigned[0]["area_id"] is None

    # 3. Search by specific area
    res_kitchen = reg.search(area_id="kitchen")
    assert len(res_kitchen) == 1
    assert res_kitchen[0]["entity_id"] == "binary_sensor.kitchen_door"
    assert res_kitchen[0]["area_name"] == "Kitchen"

    # 4. Lookup by exact friendly name
    found = reg.lookup_by_friendly_name("Kitchen Back Door")
    assert found is not None
    assert found["entity_id"] == "binary_sensor.kitchen_door"

    not_found = reg.lookup_by_friendly_name("Nonexistent Sensor")
    assert not_found is None

    # 5. Designate area
    assert reg.set_entity_area("binary_sensor.front_motion", "kitchen") is True
    assert reg.get_entity("binary_sensor.front_motion")["area_id"] == "kitchen"
    assert reg.set_entity_area("unknown_sensor", "kitchen") is False

    # 6. Check missing
    missing = reg.check_missing({"binary_sensor.kitchen_door", "sensor.ghost"})
    assert missing == ["sensor.ghost"]

    # 7. Get areas
    assert len(reg.get_areas()) == 2
    assert reg.get_area("kitchen")["name"] == "Kitchen"
    assert reg.get_area("unknown") is None
