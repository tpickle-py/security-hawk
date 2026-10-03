"""Unit tests for settings storage and HA helper registration."""

from __future__ import annotations

from settings_mgr.storage import SettingsStorage


def test_settings_storage_crud(tmp_path):
    storage = SettingsStorage(data_dir=tmp_path)
    defaults = storage.load()
    assert defaults["quiet_return_seconds"] == 120
    assert defaults["mqtt"]["enabled"] is False

    # Update settings
    new_settings = dict(defaults)
    new_settings["quiet_return_seconds"] = 180
    new_settings["mqtt"]["enabled"] = True
    new_settings["mqtt"]["host"] = "192.168.1.50"
    storage.save(new_settings)

    reloaded = storage.load()
    assert reloaded["quiet_return_seconds"] == 180
    assert reloaded["mqtt"]["enabled"] is True
    assert reloaded["mqtt"]["host"] == "192.168.1.50"


def test_settings_api_get_and_post(client, tmp_path, monkeypatch):
    from settings_mgr import storage, views

    custom_storage = SettingsStorage(data_dir=tmp_path)
    monkeypatch.setattr(storage, "settings_storage", custom_storage)
    monkeypatch.setattr(views, "settings_storage", custom_storage)

    resp = client.get("/api/settings/")
    assert resp.status_code == 200
    assert "settings" in resp.json()

    update_payload = {
        "quiet_return_seconds": 90,
        "default_view": "floor",
        "mqtt": {"enabled": True, "host": "mqtt.local", "port": 1883},
    }
    resp = client.post("/api/settings/", data=update_payload, content_type="application/json")
    assert resp.status_code == 200
    assert resp.json()["settings"]["quiet_return_seconds"] == 90

    # Bad JSON
    resp = client.post("/api/settings/", data="not json", content_type="application/json")
    assert resp.status_code == 400

    # Register HA helpers endpoint
    resp = client.post("/api/settings/register_ha_helpers/")
    assert resp.status_code == 200
    assert "count" in resp.json()
    assert "results" in resp.json()
