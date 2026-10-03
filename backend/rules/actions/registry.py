"""Action Plugin Registry for Security Hawk."""

from __future__ import annotations

import logging
from typing import Any

from rules.actions.base import ActionContext, ActionResult, BaseActionPlugin
from rules.actions.email import EmailActionPlugin
from rules.actions.ha_service import HaServiceActionPlugin
from rules.actions.webhook import WebhookActionPlugin
from rules.actions.whatsapp import WhatsAppActionPlugin

logger = logging.getLogger(__name__)


class ActionPluginRegistry:
    """Central registry for expandable Action Plugins."""

    def __init__(self) -> None:
        self._plugins: dict[str, BaseActionPlugin] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        """Register the built-in action plugins."""
        self.register(HaServiceActionPlugin())
        self.register(EmailActionPlugin())
        self.register(WhatsAppActionPlugin())
        self.register(WebhookActionPlugin())

    def register(self, plugin: BaseActionPlugin) -> None:
        """Register a new action plugin."""
        self._plugins[plugin.plugin_type] = plugin
        logger.debug("Registered action plugin: %s (%s)", plugin.name, plugin.plugin_type)

    def get_plugin(self, plugin_type: str) -> BaseActionPlugin | None:
        """Retrieve plugin by type key."""
        return self._plugins.get(plugin_type)

    def list_plugins(self) -> list[dict[str, Any]]:
        """List all available plugins and their schemas for UI consumption."""
        return [p.get_metadata() for p in self._plugins.values()]

    async def execute_action(self, action_dict: dict[str, Any], context: ActionContext) -> ActionResult:
        """Execute a single action definition."""
        plugin_type = action_dict.get("type", "")
        plugin = self.get_plugin(plugin_type)
        if not plugin:
            return ActionResult(
                success=False,
                plugin_type=plugin_type,
                error=f"Unknown action plugin type: '{plugin_type}'",
            )

        config = action_dict.get("config") or {}
        try:
            return await plugin.execute(config, context)
        except Exception as e:
            logger.error("Unhandled error in action plugin '%s': %s", plugin_type, e)
            return ActionResult(
                success=False,
                plugin_type=plugin_type,
                error=str(e),
            )

    async def execute_actions(
        self,
        actions: list[dict[str, Any]],
        context: ActionContext,
        legacy_service_call: dict[str, Any] | None = None,
    ) -> list[ActionResult]:
        """Execute all configured actions for a rule with legacy fallback."""
        results: list[ActionResult] = []

        # Execute new expandable action list
        for action in actions:
            if action.get("enabled", True) is False:
                continue
            res = await self.execute_action(action, context)
            results.append(res)

        # Backwards compatibility: execute legacy service_call if present and not duplicated
        if legacy_service_call and isinstance(legacy_service_call, dict):
            domain = legacy_service_call.get("domain")
            service = legacy_service_call.get("service")
            if domain and service:
                # Check if already covered by an action
                already_covered = any(
                    a.get("type") == "ha_service"
                    and a.get("config", {}).get("domain") == domain
                    and a.get("config", {}).get("service") == service
                    for a in actions
                )
                if not already_covered:
                    res = await self.execute_action(
                        {
                            "type": "ha_service",
                            "config": {
                                "domain": domain,
                                "service": service,
                                "data": legacy_service_call.get("service_data")
                                or legacy_service_call.get("data")
                                or {},
                            },
                        },
                        context,
                    )
                    results.append(res)

        return results


action_registry = ActionPluginRegistry()
