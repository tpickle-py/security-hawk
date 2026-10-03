"""Settings persistence for Security Hawk app behaviors, MQTT, and HA helpers."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from django.conf import settings

logger = logging.getLogger(__name__)

DEFAULT_SETTINGS: dict[str, Any] = {
    "quiet_return_seconds": 120,
    "auto_dismiss_camera_seconds": 30,
    "default_view": "overview",
    "mqtt": {
        "enabled": False,
        "host": "core-mosquitto",
        "port": 1883,
        "username": "",
        "password": "",
        "topic_prefix": "security_hawk/",
        "ha_discovery": True,
    },
    "helpers": {
        "auto_register_synthetic_sensors": True,
        "prefix": "security_hawk_",
    },
    "notifications": {
        "email": {
            "smtp_host": "",
            "smtp_port": 587,
            "smtp_user": "",
            "smtp_password": "",
            "smtp_from": "",
            "default_to": "",
            "smtp_use_tls": True,
        },
        "whatsapp": {
            "provider": "callmebot",
            "default_phone": "",
            "api_key": "",
            "account_sid": "",
            "from_phone": "",
        },
    },
}


class SettingsStorage:
    """Read and write settings.json in DATA_DIR."""

    def __init__(self, data_dir: Path | None = None) -> None:
        self.data_dir = data_dir or Path(getattr(settings, "DATA_DIR", "/data"))
        self.settings_file = self.data_dir / "settings.json"

    def load(self) -> dict[str, Any]:
        """Load settings from JSON, returning defaults if not found."""
        if not self.settings_file.exists():
            return dict(DEFAULT_SETTINGS)

        try:
            with open(self.settings_file, encoding="utf-8") as f:
                data = json.load(f)
                merged = dict(DEFAULT_SETTINGS)
                merged.update(data)
                return merged
        except Exception as e:
            logger.error("Failed to load settings file, using defaults: %s", e)
            return dict(DEFAULT_SETTINGS)

    def save(self, data: dict[str, Any]) -> dict[str, Any]:
        """Persist settings to disk atomically."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        merged = dict(DEFAULT_SETTINGS)
        merged.update(data)

        tmp_file = self.data_dir / "settings.json.tmp"
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(merged, f, indent=2)
        tmp_file.replace(self.settings_file)
        logger.info("Saved settings to %s", self.settings_file)
        return merged


settings_storage = SettingsStorage()
