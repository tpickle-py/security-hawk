"""Slack Incoming Webhook Notification Action Plugin."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

from rules.actions.base import ActionContext, ActionResult, BaseActionPlugin
from settings_mgr.storage import settings_storage

logger = logging.getLogger(__name__)


class SlackActionPlugin(BaseActionPlugin):
    """Sends formatted alert messages to Slack channels via Incoming Webhooks."""

    plugin_type = "slack"
    name = "Slack Webhook"
    description = "Send formatted Block Kit alert notifications to Slack channels."
    icon = "slack"

    def get_fields(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "webhook_url",
                "label": "Slack Webhook URL",
                "type": "text",
                "required": True,
                "placeholder": "https://hooks.slack.com/services/...",
            },
            {
                "name": "channel",
                "label": "Channel Override (optional)",
                "type": "text",
                "placeholder": "#security-alerts",
            },
            {
                "name": "message",
                "label": "Custom Message Text",
                "type": "textarea",
                "required": False,
                "placeholder": "Security alert detected: {rule_name}",
                "default": "🚨 *Security Hawk Alert Triggered: {rule_name}*",
            },
        ]

    async def execute(self, config: dict[str, Any], context: ActionContext) -> ActionResult:
        app_settings = settings_storage.load()
        slack_defaults = app_settings.get("notifications", {}).get("slack", {})

        url = config.get("webhook_url") or slack_defaults.get("webhook_url") or ""
        if not url:
            return ActionResult(
                success=False,
                plugin_type=self.plugin_type,
                error="Slack Webhook URL is required.",
            )

        text_msg = context.format_text(config.get("message") or "🚨 *Security Hawk Alert Triggered*")
        triggered_entities = ", ".join(context.triggered_by) if context.triggered_by else "None"

        payload: dict[str, Any] = {
            "text": text_msg,
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"🚨 Security Alert: {context.rule_name}",
                        "emoji": True,
                    },
                },
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": text_msg},
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Sensors:*\n{triggered_entities}"},
                        {"type": "mrkdwn", "text": f"*Synthetic Entity:*\n`{context.output_entity_id or 'N/A'}`"},
                    ],
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"Rule ID: `{context.rule_id}` | Security Hawk Live Automation",
                        }
                    ],
                },
            ],
        }

        channel = config.get("channel") or slack_defaults.get("channel")
        if channel:
            payload["channel"] = channel

        try:
            async with (
                aiohttp.ClientSession() as session,
                session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp,
            ):
                if resp.status in (200, 204):
                    return ActionResult(
                        success=True,
                        plugin_type=self.plugin_type,
                        message="Slack notification sent successfully.",
                    )
                text = await resp.text()
                return ActionResult(
                    success=False,
                    plugin_type=self.plugin_type,
                    error=f"Slack webhook returned HTTP {resp.status}: {text[:120]}",
                )
        except Exception as e:
            logger.error("Slack action error: %s", e)
            return ActionResult(
                success=False,
                plugin_type=self.plugin_type,
                error=str(e),
            )
