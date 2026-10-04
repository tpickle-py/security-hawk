"""Tests for plan export, import, and version rollback views."""

import io
import json
import os
import zipfile
from unittest.mock import patch

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
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


def test_export_bundle_zip(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "ASSETS_DIR", tmp_path / "assets")
    storage = PlanStorage(str(tmp_path / "plans"), str(tmp_path / "versions"))
    storage.save("bundle_plan", _sample_plan("Bundle Manor"))

    # Write dummy asset
    asset_dir = tmp_path / "assets" / "bundle_plan"
    os.makedirs(asset_dir, exist_ok=True)
    with open(asset_dir / "blueprint.png", "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\nfakeimagecontent")

    client = Client()
    with patch("plans.views.get_storage", return_value=storage):
        res = client.get("/api/plans/bundle_plan/bundle/")
        assert res.status_code == 200
        assert res["Content-Type"] == "application/zip"
        assert "bundle-manor_bundle.zip" in res["Content-Disposition"]

        zf = zipfile.ZipFile(io.BytesIO(res.content))
        names = zf.namelist()
        assert "plan.json" in names
        assert "assets/blueprint.png" in names

        imported_json = json.loads(zf.read("plan.json").decode("utf-8"))
        assert imported_json["name"] == "Bundle Manor"
        assert zf.read("assets/blueprint.png") == b"\x89PNG\r\n\x1a\nfakeimagecontent"


def test_import_plan_bundle_zip(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "ASSETS_DIR", tmp_path / "assets")
    storage = PlanStorage(str(tmp_path / "plans"), str(tmp_path / "versions"))

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("plan.json", json.dumps(_sample_plan("Unpacked Villa")))
        zf.writestr("assets/floor1.svg", "<svg>test</svg>")

    uploaded_zip = SimpleUploadedFile("villa.zip", zip_buf.getvalue(), content_type="application/zip")

    client = Client()
    with patch("plans.views.get_storage", return_value=storage):
        res = client.post("/api/plans/import/", data={"file": uploaded_zip})
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "imported"
        assert data["is_bundle"] is True
        assert data["plan"]["name"] == "Unpacked Villa"

        target_id = data["plan_id"]
        # Check asset extracted
        extracted_asset = tmp_path / "assets" / target_id / "floor1.svg"
        assert os.path.exists(extracted_asset)
        with open(extracted_asset) as f:
            assert f.read() == "<svg>test</svg>"


def test_import_plan_bundle_missing_json(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "ASSETS_DIR", tmp_path / "assets")
    storage = PlanStorage(str(tmp_path / "plans"), str(tmp_path / "versions"))

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("notes.txt", "No plan here")

    uploaded_zip = SimpleUploadedFile("empty.zip", zip_buf.getvalue(), content_type="application/zip")

    client = Client()
    with patch("plans.views.get_storage", return_value=storage):
        res = client.post("/api/plans/import/", data={"file": uploaded_zip})
        assert res.status_code == 400
        assert "No plan.json found" in res.json()["error"]

