"""Tests for plan schema migration engine."""

from plans.migrations import CURRENT_SCHEMA_VERSION, migrate_plan_data


def test_migrate_v1_to_v2():
    v1_plan = {
        "schema_version": 1,
        "name": "My Test Home",
        "overview": {
            "id": "fl_overview",
            "name": "Site Overview",
            "endpoints": [
                {
                    "id": "ep_1",
                    "entity_id": "binary_sensor.front_door",
                    "type": "door",
                    "x": 100,
                    "y": 200,
                    "label": "Front Door",
                }
            ],
        },
        "buildings": [
            {
                "id": "bld_main",
                "name": "Main House",
                "x": 0,
                "y": 0,
                "floors": [
                    {
                        "id": "fl_ground",
                        "name": "Ground Floor",
                        "endpoints": [
                            {
                                "id": "ep_2",
                                "entity_id": "binary_sensor.motion_living",
                                "type": "motion",
                                "x": 150,
                                "y": 250,
                                "label": "Living Room Motion",
                            }
                        ],
                    }
                ],
            }
        ],
    }

    migrated, was_modified = migrate_plan_data(v1_plan)

    assert was_modified is True
    assert migrated["schema_version"] == CURRENT_SCHEMA_VERSION
    assert CURRENT_SCHEMA_VERSION == 2

    # Check overview floor defaults
    overview = migrated["overview"]
    assert "shapes" in overview
    assert overview["shapes"] == []
    assert "sub_areas" in overview
    assert overview["sub_areas"] == []

    # Check overview endpoint defaults
    ep1 = overview["endpoints"][0]
    assert ep1["parent_id"] is None
    assert ep1["group_id"] is None
    assert ep1["group_name"] is None
    assert ep1["stale_after"] is None
    assert ep1["companions"] == []
    assert ep1["cameras"] == []

    # Check building floor defaults
    floor = migrated["buildings"][0]["floors"][0]
    assert "shapes" in floor
    assert floor["shapes"] == []
    assert "sub_areas" in floor
    assert floor["sub_areas"] == []

    ep2 = floor["endpoints"][0]
    assert ep2["parent_id"] is None
    assert ep2["group_id"] is None
    assert ep2["stale_after"] is None


def test_migrate_already_current_v2():
    v2_plan = {
        "schema_version": 2,
        "name": "Already V2",
        "overview": {
            "id": "fl_overview",
            "name": "Site Overview",
            "shapes": [],
            "sub_areas": [],
            "endpoints": [],
        },
        "buildings": [],
    }

    migrated, was_modified = migrate_plan_data(v2_plan)
    assert was_modified is False
    assert migrated["schema_version"] == 2
