"""Tests for plan export, import, and version rollback views."""

import json
from unittest.mock import patch

from django.test import Client

from plans.storage import PlanStorage


def _sample_plan(name="Test House"):
    return {
        "schema_version": 2,
        "name": name,
        "overview": {
            "id": "fl_overview",
            "name": "Site Overview",
            "shapes": [],
            "sub_areas": [],
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
        "buildings": [],
    }


def test_export_plan(tmp_path):
    storage = PlanStorage(str(tmp_path / "plans"), str(tmp_path / "versions"))
    storage.save("test_export", _sample_plan("My Estate"))

    client = Client()
    with patch("plans.views.get_storage", return_value=storage):
        res = client.get("/api/plans/test_export/export/")
        assert res.status_code == 200
        assert res["Content-Type"] == "application/json"
        assert "my-estate_plan.json" in res["Content-Disposition"]

        data = json.loads(res.content)
        assert data["name"] == "My Estate"
        assert data["schema_version"] == 2


def test_import_plan_json_body(tmp_path):
    storage = PlanStorage(str(tmp_path / "plans"), str(tmp_path / "versions"))
    client = Client()

    plan_payload = _sample_plan("Imported Home")
    with patch("plans.views.get_storage", return_value=storage):
        res = client.post(
            "/api/plans/import/",
            data=json.dumps(plan_payload),
            content_type="application/json",
        )
        assert res.status_code == 200
        res_data = res.json()
        assert res_data["status"] == "imported"
        assert res_data["plan"]["name"] == "Imported Home"
        assert res_data["migrated"] is False


def test_import_legacy_v1_plan_triggers_migration(tmp_path):
    storage = PlanStorage(str(tmp_path / "plans"), str(tmp_path / "versions"))
    client = Client()

    v1_payload = {
        "schema_version": 1,
        "name": "Legacy V1",
        "overview": {
            "id": "fl_overview",
            "name": "Site Overview",
            "endpoints": [],
        },
        "buildings": [],
    }

    with patch("plans.views.get_storage", return_value=storage):
        res = client.post(
            "/api/plans/import/",
            data=json.dumps(v1_payload),
            content_type="application/json",
        )
        assert res.status_code == 200
        res_data = res.json()
        assert res_data["status"] == "imported"
        assert res_data["migrated"] is True
        assert res_data["plan"]["schema_version"] == 2
        assert "shapes" in res_data["plan"]["overview"]


def test_versions_and_restore(tmp_path):
    storage = PlanStorage(str(tmp_path / "plans"), str(tmp_path / "versions"))
    client = Client()

    # Save version 1
    storage.save("roll_test", _sample_plan("Version 1"))
    # Save version 2 (overwrites, creating snapshot of Version 1)
    storage.save("roll_test", _sample_plan("Version 2"))

    with patch("plans.views.get_storage", return_value=storage):
        # List versions
        v_res = client.get("/api/plans/roll_test/versions/")
        assert v_res.status_code == 200
        versions = v_res.json()["versions"]
        assert len(versions) == 1

        snap_filename = versions[0]["filename"]

        # Restore version 1 snapshot
        r_res = client.post(
            "/api/plans/roll_test/restore/",
            data=json.dumps({"version": snap_filename}),
            content_type="application/json",
        )
        assert r_res.status_code == 200
        assert r_res.json()["plan"]["name"] == "Version 1"
