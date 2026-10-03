"""WhatsApp Notification Action Plugin."""

from __future__ import annotations

import logging
import urllib.parse
from typing import Any

import aiohttp

from rules.actions.base import ActionContext, ActionResult, BaseActionPlugin
from settings_mgr.storage import settings_storage

logger = logging.getLogger(__name__)


class WhatsAppActionPlugin(BaseActionPlugin):
    """Sends WhatsApp alerts via CallMeBot, Twilio, or generic webhook gateway."""

    plugin_type = "whatsapp"
    name = "WhatsApp Message"
    description = "Send instant WhatsApp alerts (CallMeBot, Twilio, or Webhook)."
    icon = "whatsapp"

    def get_fields(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "provider",
                "label": "Provider",
                "type": "select",
                "options": [
                    {"label": "CallMeBot (Free & Simple for HA)", "value": "callmebot"},
                    {"label": "Custom Gateway / Webhook", "value": "custom_webhook"},
                    {"label": "Twilio WhatsApp", "value": "twilio"},
                ],
                "default": "callmebot",
            },
            {
                "name": "phone",
                "label": "Phone Number (E.164 e.g. +14155552671)",
                "type": "text",
                "required": True,
                "placeholder": "+1234567890",
            },
            {
                "name": "api_key",
                "label": "API Key / Token",
                "type": "password",
                "required": False,
                "placeholder": "CallMeBot API Key or Twilio Auth Token",
            },
            {
                "name": "message",
                "label": "Message Text",
                "type": "textarea",
                "required": False,
                "placeholder": "🚨 Security Hawk Alert: {rule_name} triggered by {entities}",
                "default": "🚨 *Security Hawk Alert*\nRule *{rule_name}* was triggered by: {entities}\nSynthetic ID: {output_entity_id}",
            },
            {
                "name": "webhook_url",
                "label": "Gateway Webhook URL (only for Custom Gateway)",
                "type": "text",
                "placeholder": "https://your-whatsapp-gateway.local/send",
            },
        ]

    async def execute(self, config: dict[str, Any], context: ActionContext) -> ActionResult:
        app_settings = settings_storage.load()
        wa_defaults = app_settings.get("notifications", {}).get("whatsapp", {})

        provider = config.get("provider") or wa_defaults.get("provider") or "callmebot"
        phone = config.get("phone") or wa_defaults.get("default_phone") or ""
        api_key = config.get("api_key") or wa_defaults.get("api_key") or ""
        message_template = config.get("message") or (
            "🚨 Security Hawk Alert: Rule {rule_name} triggered by {entities}"
        )
        message = context.format_text(message_template)

        if not phone:
            return ActionResult(
                success=False,
                plugin_type=self.plugin_type,
                error="Recipient phone number is required.",
            )

        try:
            async with aiohttp.ClientSession() as session:
                if provider == "callmebot":
                    if not api_key:
                        return ActionResult(
                            success=False,
                            plugin_type=self.plugin_type,
                            error="CallMeBot API Key is required.",
                        )
                    # Clean phone number (CallMeBot expects phone with or without leading +)
                    clean_phone = phone.strip()
                    encoded_text = urllib.parse.quote(message)
                    url = (
                        f"https://api.callmebot.com/whatsapp.php"
                        f"?phone={clean_phone}&text={encoded_text}&apikey={api_key.strip()}"
                    )
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                        if resp.status == 200:
                            return ActionResult(
                                success=True,
                                plugin_type=self.plugin_type,
                                message="WhatsApp message dispatched via CallMeBot.",
                            )
                        text = await resp.text()
                        return ActionResult(
                            success=False,
                            plugin_type=self.plugin_type,
                            error=f"CallMeBot returned HTTP {resp.status}: {text[:100]}",
                        )

                elif provider == "twilio":
                    account_sid = config.get("account_sid") or wa_defaults.get("account_sid") or ""
                    from_phone = (
                        config.get("from_phone") or wa_defaults.get("from_phone") or "whatsapp:+14155238886"
                    )
                    if not account_sid or not api_key:
                        return ActionResult(
                            success=False,
                            plugin_type=self.plugin_type,
                            error="Twilio Account SID and Auth Token are required.",
                        )
                    url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
                    data = {
                        "From": from_phone if from_phone.startswith("whatsapp:") else f"whatsapp:{from_phone}",
                        "To": phone if phone.startswith("whatsapp:") else f"whatsapp:{phone}",
                        "Body": message,
                    }
                    import base64

                    b64_auth = base64.b64encode(f"{account_sid}:{api_key}".encode()).decode()
                    headers = {"Authorization": f"Basic {b64_auth}"}
                    async with session.post(
                        url, data=data, headers=headers, timeout=aiohttp.ClientTimeout(total=10)
                    ) as resp:
                        if resp.status in (200, 201):
                            return ActionResult(
                                success=True,
                                plugin_type=self.plugin_type,
                                message="WhatsApp message dispatched via Twilio.",
                            )
                        text = await resp.text()
                        return ActionResult(
                            success=False,
                            plugin_type=self.plugin_type,
                            error=f"Twilio error {resp.status}: {text[:100]}",
                        )

                else:
                    # Custom Webhook gateway
                    url = config.get("webhook_url") or wa_defaults.get("webhook_url") or ""
                    if not url:
                        return ActionResult(
                            success=False,
                            plugin_type=self.plugin_type,
                            error="Webhook URL is required for custom WhatsApp gateway.",
                        )
                    payload = {"phone": phone, "message": message, "rule_id": context.rule_id}
                    headers = {}
                    if api_key:
                        headers["Authorization"] = f"Bearer {api_key}"
                    async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                        return ActionResult(
                            success=resp.status in (200, 201, 202, 204),
                            plugin_type=self.plugin_type,
                            message=f"WhatsApp webhook executed (HTTP {resp.status}).",
                        )

        except Exception as e:
            logger.error("Failed to send WhatsApp message: %s", e)
            return ActionResult(
                success=False,
                plugin_type=self.plugin_type,
                error=str(e),
            )
