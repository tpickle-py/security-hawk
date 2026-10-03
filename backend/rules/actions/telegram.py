"""Telegram Bot Notification Action Plugin."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

from rules.actions.base import ActionContext, ActionResult, BaseActionPlugin
from settings_mgr.storage import settings_storage

logger = logging.getLogger(__name__)


class TelegramActionPlugin(BaseActionPlugin):
    """Sends alert messages to Telegram chats or groups via Telegram Bot API."""

    plugin_type = "telegram"
    name = "Telegram Bot"
    description = "Send instant notifications to Telegram users or group chats."
    icon = "telegram"

    def get_fields(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "chat_id",
                "label": "Chat ID / Group ID",
                "type": "text",
                "required": True,
                "placeholder": "123456789 or -100123456789",
            },
            {
                "name": "bot_token",
                "label": "Bot Token (optional override)",
                "type": "password",
                "placeholder": "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
            },
            {
                "name": "message",
                "label": "Message Text",
                "type": "textarea",
                "required": False,
                "placeholder": "🚨 *Security Alert:* {rule_name} triggered by {entities}",
                "default": "🚨 *Security Hawk Alert*\n\nRule: *{rule_name}*\nSensors: {entities}\nSynthetic ID: `{output_entity_id}`",
            },
            {
                "name": "silent",
                "label": "Silent Notification (no sound)",
                "type": "select",
                "options": [
                    {"label": "No (Normal notification)", "value": "false"},
                    {"label": "Yes (Deliver silently)", "value": "true"},
                ],
                "default": "false",
            },
        ]

    async def execute(self, config: dict[str, Any], context: ActionContext) -> ActionResult:
        app_settings = settings_storage.load()
        tg_defaults = app_settings.get("notifications", {}).get("telegram", {})

        token = config.get("bot_token") or tg_defaults.get("bot_token") or ""
        chat_id = config.get("chat_id") or tg_defaults.get("default_chat_id") or ""

        if not token or not chat_id:
            return ActionResult(
                success=False,
                plugin_type=self.plugin_type,
                error="Both Telegram Bot Token and Chat ID are required.",
            )

        message_template = config.get("message") or (
            "🚨 *Security Hawk Alert*\nRule: *{rule_name}*\nSensors: {entities}"
        )
        text = context.format_text(message_template)
        silent = str(config.get("silent", "false")).lower() == "true"

        url = f"https://api.telegram.org/bot{token.strip()}/sendMessage"
        payload = {
            "chat_id": chat_id.strip(),
            "text": text,
            "parse_mode": "Markdown",
            "disable_notification": silent,
        }

        try:
            async with (
                aiohttp.ClientSession() as session,
                session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp,
            ):
                if resp.status in (200, 201):
                    return ActionResult(
                        success=True,
                        plugin_type=self.plugin_type,
                        message="Telegram message sent successfully.",
                    )
                try:
                    resp_json = await resp.json()
                except Exception:
                    resp_json = {}
                desc = resp_json.get("description", "") if isinstance(resp_json, dict) else ""
                return ActionResult(
                    success=False,
                    plugin_type=self.plugin_type,
                    error=f"Telegram API error {resp.status}: {desc}",
                )
        except Exception as e:
            logger.error("Telegram action error: %s", e)
            return ActionResult(
                success=False,
                plugin_type=self.plugin_type,
                error=str(e),
            )
