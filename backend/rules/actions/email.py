"""SMTP Email Notification Action Plugin."""

from __future__ import annotations

import asyncio
import logging
import smtplib
from email.message import EmailMessage
from typing import Any

from rules.actions.base import ActionContext, ActionResult, BaseActionPlugin
from settings_mgr.storage import settings_storage

logger = logging.getLogger(__name__)


def _send_smtp_sync(
    host: str,
    port: int,
    user: str,
    password: str,
    from_addr: str,
    to_addrs: list[str],
    subject: str,
    body: str,
    use_tls: bool,
) -> None:
    """Synchronous worker to send email via smtplib."""
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_addr or user or "security-hawk@local"
    msg["To"] = ", ".join(to_addrs)
    msg.set_content(body)

    if use_tls:
        with smtplib.SMTP(host, port, timeout=10) as server:
            server.starttls()
            if user and password:
                server.login(user, password)
            server.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=10) as server:
            if user and password:
                server.login(user, password)
            server.send_message(msg)


class EmailActionPlugin(BaseActionPlugin):
    """Sends email notifications via SMTP."""

    plugin_type = "email"
    name = "Email Notification (SMTP)"
    description = "Send security alert emails via standard SMTP."
    icon = "email"

    def get_fields(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "to",
                "label": "Recipient Email(s)",
                "type": "text",
                "required": True,
                "placeholder": "admin@example.com, security@example.com",
            },
            {
                "name": "subject",
                "label": "Subject",
                "type": "text",
                "required": False,
                "placeholder": "[Security Hawk] Alert: {rule_name}",
                "default": "[Security Hawk Alert] {rule_name} Triggered",
            },
            {
                "name": "body",
                "label": "Message Body",
                "type": "textarea",
                "required": False,
                "placeholder": "Security Hawk detected an event: {rule_name}\nTriggered by: {entities}",
                "default": "Security Hawk Alert:\nRule '{rule_name}' was triggered by sensors: {entities}.\nSynthetic entity: {output_entity_id}",
            },
            {
                "name": "smtp_host",
                "label": "SMTP Host (optional override)",
                "type": "text",
                "placeholder": "Leave empty to use global Settings",
            },
            {
                "name": "smtp_port",
                "label": "SMTP Port (optional override)",
                "type": "number",
                "placeholder": "587",
            },
        ]

    async def execute(self, config: dict[str, Any], context: ActionContext) -> ActionResult:
        # Load global settings for fallback
        app_settings = settings_storage.load()
        email_defaults = app_settings.get("notifications", {}).get("email", {})

        to_raw = config.get("to", "").strip() or email_defaults.get("default_to", "")
        if not to_raw:
            return ActionResult(
                success=False,
                plugin_type=self.plugin_type,
                error="No recipient email address specified.",
            )

        to_addrs = [addr.strip() for addr in to_raw.split(",") if addr.strip()]
        subject_template = config.get("subject") or "[Security Hawk Alert] {rule_name} Triggered"
        body_template = config.get("body") or (
            "Security Hawk Alert:\nRule '{rule_name}' triggered by: {entities}."
        )

        subject = context.format_text(subject_template)
        body = context.format_text(body_template)

        host = config.get("smtp_host") or email_defaults.get("smtp_host") or "localhost"
        port = int(config.get("smtp_port") or email_defaults.get("smtp_port") or 587)
        user = config.get("smtp_user") or email_defaults.get("smtp_user") or ""
        password = config.get("smtp_password") or email_defaults.get("smtp_password") or ""
        from_addr = email_defaults.get("smtp_from") or user
        use_tls = bool(config.get("smtp_use_tls", email_defaults.get("smtp_use_tls", True)))

        try:
            await asyncio.to_thread(
                _send_smtp_sync,
                host=host,
                port=port,
                user=user,
                password=password,
                from_addr=from_addr,
                to_addrs=to_addrs,
                subject=subject,
                body=body,
                use_tls=use_tls,
            )
            return ActionResult(
                success=True,
                plugin_type=self.plugin_type,
                message=f"Email sent successfully to {len(to_addrs)} recipient(s).",
            )
        except Exception as e:
            logger.error("Failed to send alert email: %s", e)
            return ActionResult(
                success=False,
                plugin_type=self.plugin_type,
                error=str(e),
            )
