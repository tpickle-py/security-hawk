from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ActionContext:
    """Runtime context passed to action plugins when a rule triggers."""

    rule_id: str
    rule_name: str
    triggered_by: list[str]
    time_epoch: float
    output_entity_id: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def format_text(self, template: str) -> str:
        """Interpolate common variables into templates."""
        entities_str = ", ".join(self.triggered_by) if self.triggered_by else "None"
        replacements = {
            "{rule_id}": self.rule_id,
            "{rule_name}": self.rule_name,
            "{entities}": entities_str,
            "{output_entity_id}": self.output_entity_id or "",
        }
        text = template
        for k, v in replacements.items():
            text = text.replace(k, str(v))
        return text


@dataclass
class ActionResult:
    """Outcome of an action execution."""

    success: bool
    plugin_type: str
    message: str = ""
    error: str | None = None


class BaseActionPlugin:
    """Abstract base class for all Rule Action Plugins."""

    plugin_type: str = "base"
    name: str = "Base Action"
    description: str = ""
    icon: str = "cog"

    def get_metadata(self) -> dict[str, Any]:
        """Metadata and field specifications for frontend UI rendering."""
        return {
            "type": self.plugin_type,
            "name": self.name,
            "description": self.description,
            "icon": self.icon,
            "fields": self.get_fields(),
        }

    def get_fields(self) -> list[dict[str, Any]]:
        """Return UI form fields required by this plugin."""
        return []

    async def execute(self, config: dict[str, Any], context: ActionContext) -> ActionResult:
        """Execute the action with given configuration and context."""
        raise NotImplementedError
