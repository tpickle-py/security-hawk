"""Unit tests for expandable Rule Action Plugins (HA Service, Email, WhatsApp, Webhook)."""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rules.actions import ActionContext, ActionPluginRegistry, action_registry
from rules.actions.email import EmailActionPlugin
from rules.actions.ha_service import HaServiceActionPlugin
from rules.actions.webhook import WebhookActionPlugin
from rules.actions.whatsapp import WhatsAppActionPlugin


def test_action_context_format_text():
    ctx = ActionContext(
        rule_id="rule_123",
        rule_name="Backyard Intrusion",
        triggered_by=["binary_sensor.motion_backyard", "camera.backyard"],
        time_epoch=time.time(),
        output_entity_id="binary_sensor.security_hawk_backyard",
    )
    msg = ctx.format_text("Alert! {rule_name} fired by {entities}. Target: {output_entity_id}")
    assert "Backyard Intrusion" in msg
    assert "binary_sensor.motion_backyard" in msg
    assert "binary_sensor.security_hawk_backyard" in msg


def test_action_registry_plugins():
    plugins = action_registry.list_plugins()
    types = {p["type"] for p in plugins}
    assert "ha_service" in types
    assert "email" in types
    assert "whatsapp" in types
    assert "webhook" in types

    for p in plugins:
        assert "name" in p
        assert "description" in p
        assert "fields" in p
        assert len(p["fields"]) > 0


@pytest.mark.asyncio
async def test_ha_service_action_plugin():
    mock_ha = MagicMock()
    mock_ha.call_service = AsyncMock(return_value={"success": True})
    plugin = HaServiceActionPlugin(ha_client=mock_ha)

    ctx = ActionContext(
        rule_id="r1",
        rule_name="Test Rule",
        triggered_by=["sensor.test"],
        time_epoch=time.time(),
    )

    # Valid execution
    res = await plugin.execute(
        {
            "domain": "alarm_control_panel",
            "service": "alarm_trigger",
            "data": {"message": "Breach in {rule_name}"},
        },
        ctx,
    )
    assert res.success is True
    assert "executed successfully" in res.message
    mock_ha.call_service.assert_called_once_with(
        domain="alarm_control_panel",
        service="alarm_trigger",
        service_data={"message": "Breach in Test Rule"},
    )

    # Missing domain/service
    res_err = await plugin.execute({}, ctx)
    assert res_err.success is False
    assert "required" in res_err.error


@pytest.mark.asyncio
async def test_email_action_plugin(monkeypatch):
    plugin = EmailActionPlugin()
    ctx = ActionContext(
        rule_id="r2",
        rule_name="Porch Package",
        triggered_by=["camera.porch"],
        time_epoch=time.time(),
    )

    sent_emails = []

    def mock_send_smtp_sync(host, port, user, password, from_addr, to_addrs, subject, body, use_tls):
        sent_emails.append({
            "to": to_addrs,
            "subject": subject,
            "body": body,
            "host": host,
        })

    monkeypatch.setattr("rules.actions.email._send_smtp_sync", mock_send_smtp_sync)

    res = await plugin.execute(
        {
            "to": "owner@example.com, guard@example.com",
            "subject": "Alert: {rule_name}",
            "body": "Package detected by {entities}",
            "smtp_host": "smtp.test.local",
        },
        ctx,
    )
    assert res.success is True
    assert len(sent_emails) == 1
    assert sent_emails[0]["to"] == ["owner@example.com", "guard@example.com"]
    assert sent_emails[0]["subject"] == "Alert: Porch Package"
    assert "camera.porch" in sent_emails[0]["body"]

    # Missing recipient
    res_err = await plugin.execute({"to": ""}, ctx)
    assert res_err.success is False


@pytest.mark.asyncio
async def test_whatsapp_action_plugin_callmebot():
    plugin = WhatsAppActionPlugin()
    ctx = ActionContext(
        rule_id="r3",
        rule_name="Pool Gate Open",
        triggered_by=["binary_sensor.pool_gate"],
        time_epoch=time.time(),
    )

    mock_resp = AsyncMock()
    mock_resp.status = 200

    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_get.return_value.__aenter__.return_value = mock_resp

        res = await plugin.execute(
            {
                "provider": "callmebot",
                "phone": "+1234567890",
                "api_key": "secret123",
                "message": "Gate breach: {rule_name}",
            },
            ctx,
        )
        assert res.success is True
        assert "CallMeBot" in res.message


@pytest.mark.asyncio
async def test_whatsapp_action_plugin_twilio():
    plugin = WhatsAppActionPlugin()
    ctx = ActionContext(
        rule_id="r3_tw",
        rule_name="Perimeter Breach",
        triggered_by=["binary_sensor.fence"],
        time_epoch=time.time(),
    )

    mock_resp = AsyncMock()
    mock_resp.status = 201

    with patch("aiohttp.ClientSession.post") as mock_post:
        mock_post.return_value.__aenter__.return_value = mock_resp

        res = await plugin.execute(
            {
                "provider": "twilio",
                "phone": "+1234567890",
                "api_key": "auth_token_xyz",
                "account_sid": "AC123456",
            },
            ctx,
        )
        assert res.success is True
        assert "Twilio" in res.message


@pytest.mark.asyncio
async def test_webhook_action_plugin():
    plugin = WebhookActionPlugin()
    ctx = ActionContext(
        rule_id="r4",
        rule_name="Server Room Hot",
        triggered_by=["sensor.temp"],
        time_epoch=time.time(),
    )

    # POST webhook
    mock_resp = AsyncMock()
    mock_resp.status = 200

    with patch("aiohttp.ClientSession.post") as mock_post:
        mock_post.return_value.__aenter__.return_value = mock_resp

        res = await plugin.execute(
            {
                "url": "https://webhook.site/test",
                "method": "POST",
                "payload": {"alert": "{rule_name}"},
            },
            ctx,
        )
        assert res.success is True
        assert "POST" in res.message

    # GET webhook
    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_get.return_value.__aenter__.return_value = mock_resp

        res = await plugin.execute(
            {
                "url": "https://webhook.site/test",
                "method": "GET",
            },
            ctx,
        )
        assert res.success is True
        assert "GET" in res.message


@pytest.mark.asyncio
async def test_action_registry_execute_actions_with_legacy_fallback():
    registry = ActionPluginRegistry()
    mock_plugin = MagicMock()
    mock_plugin.plugin_type = "custom_test"

    async def mock_exec(config, context):
        from rules.actions.base import ActionResult
        return ActionResult(success=True, plugin_type="custom_test", message="ok")

    mock_plugin.execute = mock_exec
    registry.register(mock_plugin)

    ctx = ActionContext(
        rule_id="r5",
        rule_name="Multi Action Rule",
        triggered_by=["sensor.a"],
        time_epoch=time.time(),
    )

    # Execute custom action + legacy service call
    results = await registry.execute_actions(
        actions=[
            {"type": "custom_test", "config": {}, "enabled": True},
            {"type": "custom_test", "config": {}, "enabled": False},  # disabled, skipped
        ],
        context=ctx,
        legacy_service_call={
            "domain": "notify",
            "service": "notify",
            "data": {"message": "Legacy ping"},
        },
    )

    # Should have 2 results: 1 from custom_test, 1 from legacy fallback ha_service
    assert len(results) == 2
    types = [r.plugin_type for r in results]
    assert "custom_test" in types
    assert "ha_service" in types


@pytest.mark.asyncio
async def test_action_plugins_api_endpoint(async_client):
    resp = await async_client.get("/api/rules/action-plugins/")
    assert resp.status_code == 200
    data = resp.json()
    assert "plugins" in data
    types = {p["type"] for p in data["plugins"]}
    assert "ha_service" in types
    assert "email" in types
    assert "whatsapp" in types
    assert "webhook" in types
