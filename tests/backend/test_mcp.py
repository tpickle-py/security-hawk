"""Tests for Security Hawk Model Context Protocol (MCP) server endpoints."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from django.test import Client, SimpleTestCase


class TestMcpEndpoints(SimpleTestCase):
    def setUp(self) -> None:
        self.client = Client()
        self.mock_plan = {
            "id": "main_plan",
            "name": "Main Floor",
            "schema_version": 2,
            "shapes": [],
            "sub_areas": [],
            "endpoints": [
                {
                    "id": "ep_1",
                    "entity_id": "binary_sensor.front_door",
                    "type": "door",
                    "x": 100,
                    "y": 150,
                    "label": "Front Door IP: 192.168.1.50 token=secret_token_123456",
                }
            ],
        }

    def test_mcp_status(self) -> None:
        response = self.client.get("/api/mcp/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ("active", "disabled")
        assert "access_level" in data
        assert "tools_count" in data
        assert data["tools_count"] > 0

    def test_mcp_list_tools(self) -> None:
        response = self.client.get("/api/mcp/tools")
        assert response.status_code == 200
        data = response.json()
        assert "tools" in data
        tool_names = [t["name"] for t in data["tools"]]
        assert "get_floor_plan" in tool_names
        assert "add_room" in tool_names
        assert "add_subarea" in tool_names
        assert "add_wall" in tool_names
        assert "create_compound_rule" in tool_names
        assert "validate_security_coverage" in tool_names

    def test_mcp_rpc_tools_list(self) -> None:
        payload = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
        response = self.client.post(
            "/api/mcp/rpc",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert "result" in data
        assert "tools" in data["result"]
        assert len(data["result"]["tools"]) >= 6

    def test_mcp_rpc_tools_call_get_floor_plan(self) -> None:
        with (
            patch("mcp.tools._get_plan_storage") as mock_storage_factory,
        ):
            mock_storage = MagicMock()
            mock_storage.list_plans.return_value = [{"id": "main_plan", "name": "Main Floor"}]
            mock_storage.load.return_value = self.mock_plan
            mock_storage_factory.return_value = mock_storage

            payload = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": "get_floor_plan", "arguments": {}},
            }
            response = self.client.post(
                "/api/mcp/rpc",
                data=json.dumps(payload),
                content_type="application/json",
            )
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == 2
            content_text = json.loads(data["result"]["content"][0]["text"])
            assert "plan" in content_text
            assert content_text["plan"]["name"] == "Main Floor"

    def test_mcp_execute_add_room(self) -> None:
        with patch("mcp.tools._get_plan_storage") as mock_storage_factory:
            mock_storage = MagicMock()
            mock_storage.list_plans.return_value = [{"id": "main_plan"}]
            mock_storage.load.return_value = dict(self.mock_plan)
            mock_storage_factory.return_value = mock_storage

            payload = {
                "name": "add_room",
                "arguments": {
                    "name": "Living Room",
                    "points": [[0, 0], [120, 0], [120, 100], [0, 100]],
                },
            }
            response = self.client.post(
                "/api/mcp/execute",
                data=json.dumps(payload),
                content_type="application/json",
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "room_id" in data
            assert data["room"]["geometry"]["name"] == "Living Room"
            mock_storage.save.assert_called_once()

    def test_mcp_execute_add_subarea(self) -> None:
        with patch("mcp.tools._get_plan_storage") as mock_storage_factory:
            mock_storage = MagicMock()
            mock_storage.list_plans.return_value = [{"id": "main_plan"}]
            mock_storage.load.return_value = dict(self.mock_plan)
            mock_storage_factory.return_value = mock_storage

            payload = {
                "name": "add_subarea",
                "arguments": {
                    "name": "Pantry",
                    "x": 20,
                    "y": 30,
                    "width": 60,
                    "height": 50,
                },
            }
            response = self.client.post(
                "/api/mcp/execute",
                data=json.dumps(payload),
                content_type="application/json",
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "subarea_id" in data
            assert data["sub_area"]["name"] == "Pantry"
            mock_storage.save.assert_called_once()

    def test_mcp_execute_add_wall(self) -> None:
        with patch("mcp.tools._get_plan_storage") as mock_storage_factory:
            mock_storage = MagicMock()
            mock_storage.list_plans.return_value = [{"id": "main_plan"}]
            mock_storage.load.return_value = dict(self.mock_plan)
            mock_storage_factory.return_value = mock_storage

            payload = {
                "name": "add_wall",
                "arguments": {"x1": 0, "y1": 0, "x2": 200, "y2": 0, "thickness": 10},
            }
            response = self.client.post(
                "/api/mcp/execute",
                data=json.dumps(payload),
                content_type="application/json",
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "wall_id" in data
            assert data["wall"]["geometry"]["thickness"] == 10

    def test_mcp_execute_create_compound_rule(self) -> None:
        with patch("mcp.tools._get_rules_storage") as mock_rules_factory:
            mock_storage = MagicMock()
            mock_storage.create_or_update.return_value = {
                "id": "rule_test_123",
                "name": "Perimeter Breach",
                "triggers": [{"entity_id": "binary_sensor.front_door", "to_state": "on"}],
            }
            mock_rules_factory.return_value = mock_storage

            payload = {
                "name": "create_compound_rule",
                "arguments": {
                    "name": "Perimeter Breach",
                    "triggers": [{"entity_id": "binary_sensor.front_door", "to_state": "on"}],
                },
            }
            response = self.client.post(
                "/api/mcp/execute",
                data=json.dumps(payload),
                content_type="application/json",
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["rule"]["name"] == "Perimeter Breach"

    def test_mcp_execute_validate_security_coverage(self) -> None:
        with patch("mcp.tools._get_plan_storage") as mock_storage_factory:
            mock_storage = MagicMock()
            mock_storage.list_plans.return_value = [{"id": "main_plan"}]
            plan_with_room = dict(self.mock_plan)
            plan_with_room["shapes"] = [
                {"id": "s1", "type": "room", "geometry": {"name": "Master Bed", "points": [[0, 0], [10, 0], [10, 10], [0, 10]]}}
            ]
            mock_storage.load.return_value = plan_with_room
            mock_storage_factory.return_value = mock_storage

            payload = {
                "name": "validate_security_coverage",
                "arguments": {},
            }
            response = self.client.post(
                "/api/mcp/execute",
                data=json.dumps(payload),
                content_type="application/json",
            )
            assert response.status_code == 200
            data = response.json()
            assert "stats" in data
            assert data["stats"]["rooms_count"] == 1
            assert "recommendations" in data

    def test_mcp_auth_disabled(self) -> None:
        with patch(
            "mcp.auth.get_mcp_config",
            return_value={"enabled": False, "access_level": "disabled", "api_key": ""},
        ):
            response = self.client.get("/api/mcp/tools")
            assert response.status_code == 403

    def test_mcp_auth_api_key_enforcement(self) -> None:
        with patch(
            "mcp.auth.get_mcp_config",
            return_value={
                "enabled": True,
                "access_level": "full_access",
                "api_key": "my_secret_key_12345",
                "mask_sensitive_data": True,
            },
        ):
            # No key -> 403
            res1 = self.client.get("/api/mcp/tools")
            assert res1.status_code == 403

            # Wrong key -> 403
            res2 = self.client.get(
                "/api/mcp/tools",
                HTTP_AUTHORIZATION="Bearer wrong_key",
            )
            assert res2.status_code == 403

            # Correct Bearer token -> 200
            res3 = self.client.get(
                "/api/mcp/tools",
                HTTP_AUTHORIZATION="Bearer my_secret_key_12345",
            )
            assert res3.status_code == 200

            # Correct X-MCP-Key header -> 200
            res4 = self.client.get(
                "/api/mcp/tools",
                HTTP_X_MCP_KEY="my_secret_key_12345",
            )
            assert res4.status_code == 200

    def test_mcp_auth_access_levels(self) -> None:
        # read_only: can query tools, but cannot add_room
        with patch(
            "mcp.auth.get_mcp_config",
            return_value={"enabled": True, "access_level": "read_only", "api_key": "", "mask_sensitive_data": True},
        ):
            # read allowed
            res1 = self.client.get("/api/mcp/tools")
            assert res1.status_code == 200

            # mutation rejected
            res2 = self.client.post(
                "/api/mcp/execute",
                data=json.dumps({"name": "add_room", "arguments": {"name": "Test", "points": []}}),
                content_type="application/json",
            )
            assert res2.status_code == 403

        # design_only: can add room, but cannot create compound rule
        with patch(
            "mcp.auth.get_mcp_config",
            return_value={"enabled": True, "access_level": "design_only", "api_key": "", "mask_sensitive_data": True},
        ):
            res3 = self.client.post(
                "/api/mcp/execute",
                data=json.dumps({"name": "create_compound_rule", "arguments": {"name": "Test", "triggers": []}}),
                content_type="application/json",
            )
            assert res3.status_code == 403

    def test_mcp_sensitive_data_masking(self) -> None:
        with patch("mcp.tools._get_plan_storage") as mock_storage_factory:
            mock_storage = MagicMock()
            mock_storage.list_plans.return_value = [{"id": "main_plan"}]
            mock_storage.load.return_value = dict(self.mock_plan)
            mock_storage_factory.return_value = mock_storage

            payload = {"name": "get_floor_plan", "arguments": {}}
            response = self.client.post(
                "/api/mcp/execute",
                data=json.dumps(payload),
                content_type="application/json",
            )
            assert response.status_code == 200
            data = response.json()
            ep = data["plan"]["endpoints"][0]
            # Verify IP and secret token were redacted
            assert "[REDACTED_IP]" in ep["label"]
            assert "[REDACTED_TOKEN]" in ep["label"]
            assert "192.168.1.50" not in ep["label"]
            assert "secret_token_123456" not in ep["label"]
