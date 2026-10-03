"""Home Assistant Core Service Call Action Plugin."""

from __future__ import annotations

import logging
from typing import Any

from ha.client import HARestClient
from rules.actions.base import ActionContext, ActionResult, BaseActionPlugin

logger = logging.getLogger(__name__)


class HaServiceActionPlugin(BaseActionPlugin):
    """Executes a Home Assistant native service call."""

    plugin_type = "ha_service"
    name = "Home Assistant Service"
    description = "Trigger any Home Assistant Core service (alarms, lights, sirens, notify)."
    icon = "home"

    def __init__(self, ha_client: HARestClient | None = None) -> None:
        self._ha_client = ha_client or HARestClient()

    def get_fields(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "domain",
                "label": "Domain",
                "type": "text",
                "required": True,
                "placeholder": "alarm_control_panel",
                "default": "alarm_control_panel",
            },
            {
                "name": "service",
                "label": "Service",
                "type": "text",
                "required": True,
                "placeholder": "alarm_trigger",
                "default": "alarm_trigger",
            },
            {
                "name": "data",
                "label": "Service Data (JSON)",
                "type": "json",
                "required": False,
                "placeholder": '{"code": "1234"}',
                "default": {},
            },
        ]

    async def execute(self, config: dict[str, Any], context: ActionContext) -> ActionResult:
        domain = config.get("domain", "").strip()
        service = config.get("service", "").strip()
        data = config.get("data") or {}

        if not domain or not service:
            return ActionResult(
                success=False,
                plugin_type=self.plugin_type,
                error="Domain and service are required.",
            )

        try:
            # Interpolate template variables in string values if present
            service_data = {}
            if isinstance(data, dict):
                for k, v in data.items():
                    if isinstance(v, str):
                        service_data[k] = context.format_text(v)
                    else:
                        service_data[k] = v

            await self._ha_client.call_service(
                domain=domain,
                service=service,
                service_data=service_data,
            )
            return ActionResult(
                success=True,
                plugin_type=self.plugin_type,
                message=f"Service {domain}.{service} executed successfully.",
            )
        except Exception as e:
            logger.error("Failed to execute HA service %s.%s: %s", domain, service, e)
            return ActionResult(
                success=False,
                plugin_type=self.plugin_type,
                error=str(e),
            )
