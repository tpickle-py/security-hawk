"""Generic Webhook / HTTP Notification Action Plugin."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

from rules.actions.base import ActionContext, ActionResult, BaseActionPlugin

logger = logging.getLogger(__name__)


class WebhookActionPlugin(BaseActionPlugin):
    """Dispatches HTTP/Webhook requests to external endpoints (Slack, Discord, custom servers)."""

    plugin_type = "webhook"
    name = "Custom Webhook / HTTP"
    description = "Send HTTP POST/GET requests to external services, Discord, or automation systems."
    icon = "webhook"

    def get_fields(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "url",
                "label": "Webhook URL",
                "type": "text",
                "required": True,
                "placeholder": "https://discord.com/api/webhooks/... or https://maker.ifttt.com/...",
            },
            {
                "name": "method",
                "label": "HTTP Method",
                "type": "select",
                "options": [
                    {"label": "POST", "value": "POST"},
                    {"label": "GET", "value": "GET"},
                ],
                "default": "POST",
            },
            {
                "name": "payload",
                "label": "Custom JSON Payload (optional)",
                "type": "json",
                "required": False,
                "placeholder": '{"content": "Security Alert: {rule_name}"}',
            },
            {
                "name": "headers",
                "label": "HTTP Headers (JSON)",
                "type": "json",
                "required": False,
                "placeholder": '{"Authorization": "Bearer ..."}',
            },
        ]

    async def execute(self, config: dict[str, Any], context: ActionContext) -> ActionResult:
        url = config.get("url", "").strip()
        method = (config.get("method") or "POST").upper()
        custom_payload = config.get("payload")
        headers = config.get("headers") or {}

        if not url:
            return ActionResult(
                success=False,
                plugin_type=self.plugin_type,
                error="Webhook URL is required.",
            )

        # Build payload
        if custom_payload is not None:
            if isinstance(custom_payload, dict):
                payload_data = {}
                for k, v in custom_payload.items():
                    payload_data[k] = context.format_text(v) if isinstance(v, str) else v
            else:
                payload_data = custom_payload
        else:
            payload_data = {
                "event": "security_hawk_rule_triggered",
                "rule_id": context.rule_id,
                "rule_name": context.rule_name,
                "output_entity_id": context.output_entity_id,
                "triggered_by": context.triggered_by,
                "timestamp": context.time_epoch,
            }

        try:
            async with aiohttp.ClientSession() as session:
                if method == "GET":
                    async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                        return ActionResult(
                            success=resp.status in range(200, 300),
                            plugin_type=self.plugin_type,
                            message=f"Webhook GET responded with HTTP {resp.status}.",
                        )
                else:
                    async with session.post(
                        url, json=payload_data, headers=headers, timeout=aiohttp.ClientTimeout(total=10)
                    ) as resp:
                        return ActionResult(
                            success=resp.status in range(200, 300),
                            plugin_type=self.plugin_type,
                            message=f"Webhook POST responded with HTTP {resp.status}.",
                        )
        except Exception as e:
            logger.error("Failed to execute webhook for rule '%s': %s", context.rule_name, e)
            return ActionResult(
                success=False,
                plugin_type=self.plugin_type,
                error=str(e),
            )
