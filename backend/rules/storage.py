"""Rules storage for Security Hawk compound triggers and synthetic sensors."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from django.conf import settings

logger = logging.getLogger(__name__)


class RulesStorage:
    """Manages rules.json in DATA_DIR."""

    def __init__(self, data_dir: Path | None = None) -> None:
        self.data_dir = data_dir or Path(getattr(settings, "DATA_DIR", "/data"))
        self.rules_file = self.data_dir / "rules.json"

    def list_rules(self) -> list[dict[str, Any]]:
        """List all configured rules."""
        if not self.rules_file.exists():
            return []

        try:
            with open(self.rules_file, encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception as e:
            logger.error("Failed to read rules.json: %s", e)
            return []

    def get_rule(self, rule_id: str) -> dict[str, Any] | None:
        """Get a single rule by ID."""
        for r in self.list_rules():
            if r.get("id") == rule_id:
                return r
        return None

    def save_rules(self, rules: list[dict[str, Any]]) -> None:
        """Save list of rules to rules.json."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        tmp = self.data_dir / "rules.json.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(rules, f, indent=2)
        tmp.replace(self.rules_file)

    def create_or_update(self, rule_data: dict[str, Any]) -> dict[str, Any]:
        """Create or update a rule."""
        rules = self.list_rules()
        rule_id = rule_data.get("id")
        if not rule_id:
            import uuid

            rule_id = f"rule_{uuid.uuid4().hex[:8]}"
            rule_data["id"] = rule_id

        # Defaults
        rule_data.setdefault("enabled", True)
        rule_data.setdefault("logic", "ALL")
        rule_data.setdefault("time_window_seconds", 30)
        rule_data.setdefault("reset_seconds", 60)
        rule_data.setdefault("device_class", "safety")
        rule_data.setdefault("conditions", [])
        rule_data.setdefault("linked_cameras", [])

        idx = next((i for i, r in enumerate(rules) if r.get("id") == rule_id), None)
        if idx is not None:
            rules[idx] = rule_data
        else:
            rules.append(rule_data)

        self.save_rules(rules)
        return rule_data

    def delete(self, rule_id: str) -> bool:
        """Delete a rule by ID."""
        rules = self.list_rules()
        filtered = [r for r in rules if r.get("id") != rule_id]
        if len(filtered) != len(rules):
            self.save_rules(filtered)
            return True
        return False


rules_storage = RulesStorage()
