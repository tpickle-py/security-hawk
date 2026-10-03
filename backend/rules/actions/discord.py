"""Discord Webhook Notification Action Plugin."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

from rules.actions.base import ActionContext, ActionResult, BaseActionPlugin
from settings_mgr.storage import settings_storage

logger = logging.getLogger(__name__)


class DiscordActionPlugin(BaseActionPlugin):
    """Sends rich embedded alert messages to Discord channels via Webhooks."""

    plugin_type = "discord"
    name = "Discord Webhook"
    description = "Send rich embed alert cards to Discord channels."
    icon = "discord"

    def get_fields(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "webhook_url",
                "label": "Discord Webhook URL",
                "type": "text",
                "required": True,
                "placeholder": "https://discord.com/api/webhooks/...",
            },
            {
                "name": "username",
                "label": "Bot Display Name (optional)",
                "type": "text",
                "placeholder": "Security Hawk",
                "default": "Security Hawk",
            },
            {
                "name": "message",
                "label": "Alert Message / Content",
                "type": "textarea",
                "required": False,
                "placeholder": "@everyone 🚨 Security alert triggered!",
                "default": "🚨 **Security Hawk Alert Triggered**",
            },
            {
                "name": "color",
                "label": "Embed Color (Hex without #, default: EF4444 red)",
                "type": "text",
                "placeholder": "EF4444",
                "default": "EF4444",
            },
        ]

    async def execute(self, config: dict[str, Any], context: ActionContext) -> ActionResult:
        app_settings = settings_storage.load()
        discord_defaults = app_settings.get("notifications", {}).get("discord", {})

        url = config.get("webhook_url") or discord_defaults.get("webhook_url") or ""
        if not url:
            return ActionResult(
                success=False,
                plugin_type=self.plugin_type,
                error="Discord Webhook URL is required.",
            )

        content = context.format_text(config.get("message") or "🚨 **Security Hawk Alert Triggered**")
        bot_name = config.get("username") or discord_defaults.get("username") or "Security Hawk"

        # Parse color hex to integer
        color_hex = str(config.get("color") or "EF4444").lstrip("#")
        try:
            color_int = int(color_hex, 16)
        except ValueError:
            color_int = 0xEF4444

        triggered_entities = ", ".join(context.triggered_by) if context.triggered_by else "None"
        embed = {
            "title": f"Security Alert: {context.rule_name}",
            "description": f"Rule `{context.rule_name}` ({context.rule_id}) has reached trigger conditions.",
            "color": color_int,
            "fields": [
                {"name": "Triggered By Sensors", "value": triggered_entities, "inline": True},
                {"name": "Synthetic Sensor", "value": context.output_entity_id or "N/A", "inline": True},
            ],
            "footer": {"text": "Security Hawk Real-Time Monitor"},
            "timestamp": aiohttp.helpers.netrc_from_env() or None,
        }

        payload: dict[str, Any] = {
            "username": bot_name,
            "content": content,
            "embeds": [embed],
        }

        try:
            async with (
                aiohttp.ClientSession() as session,
                session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp,
            ):
                if resp.status in (200, 204):
                    return ActionResult(
                        success=True,
                        plugin_type=self.plugin_type,
                        message="Discord alert embed dispatched successfully.",
                    )
                text = await resp.text()
                return ActionResult(
                    success=False,
                    plugin_type=self.plugin_type,
                    error=f"Discord webhook failed with HTTP {resp.status}: {text[:120]}",
                )
        except Exception as e:
            logger.error("Discord action error: %s", e)
            return ActionResult(
                success=False,
                plugin_type=self.plugin_type,
                error=str(e),
            )
