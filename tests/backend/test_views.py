"""Tests for REST API views and kiosk middleware."""

from __future__ import annotations

import json
from unittest.mock import patch

from django.test import Client, SimpleTestCase, override_settings


class TestApiViews(SimpleTestCase):
    def setUp(self) -> None:
        self.client = Client()

    def test_health_check(self) -> None:
        response = self.client.get("/api/health/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["version"] == "0.1.0"

    def test_list_plans(self) -> None:
        response = self.client.get("/api/plans/")
        assert response.status_code == 200
        assert "plans" in response.json()

    def test_search_entities(self) -> None:
        with patch(
            "ha.registry.entity_registry.search", return_value=[{"entity_id": "binary_sensor.test"}]
        ):
            response = self.client.get("/api/entities/?q=test")
            assert response.status_code == 200
            data = response.json()
            assert len(data["entities"]) == 1
            assert data["entities"][0]["entity_id"] == "binary_sensor.test"

    def test_list_areas(self) -> None:
        with (
            patch(
                "ha.registry.entity_registry.get_areas",
                return_value=[{"area_id": "living_room", "name": "Living Room"}],
            ),
            patch(
                "ha.registry.entity_registry.search",
                return_value=[{"entity_id": "binary_sensor.motion", "area_id": "living_room"}],
            ),
        ):
            response = self.client.get("/api/areas/")
            assert response.status_code == 200
            data = response.json()
            assert data["total_areas"] == 1
            assert data["areas"][0]["area_id"] == "living_room"
            assert data["areas"][0]["entity_count"] == 1

    def test_lookup_friendly_name(self) -> None:
        with patch(
            "ha.registry.entity_registry.lookup_by_friendly_name",
            return_value={"entity_id": "binary_sensor.front_door", "friendly_name": "Front Door"},
        ):
            response = self.client.get("/api/entities/lookup/?name=Front Door")
            assert response.status_code == 200
            data = response.json()
            assert data["entity"]["entity_id"] == "binary_sensor.front_door"

    def test_designate_entity_area(self) -> None:
        with patch("ha.registry.entity_registry.set_entity_area", return_value=True):
            response = self.client.post(
                "/api/entities/binary_sensor.test/area/",
                data=json.dumps({"area_id": "kitchen"}),
                content_type="application/json",
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "designated"
            assert data["area_id"] == "kitchen"


class TestKioskMiddleware(SimpleTestCase):
    def setUp(self) -> None:
        self.client = Client()

    @override_settings(KIOSK_ENABLED=False, KIOSK_PORT=8100, KIOSK_TOKEN="secret123")
    def test_kiosk_disabled(self) -> None:
        # Request with kiosk port header
        response = self.client.get("/kiosk/", SERVER_PORT="8100")
        assert response.status_code == 403

    @override_settings(KIOSK_ENABLED=True, KIOSK_PORT=8100, KIOSK_TOKEN="secret123")
    def test_kiosk_missing_token(self) -> None:
        response = self.client.get("/kiosk/", SERVER_PORT="8100")
        assert response.status_code == 403

    @override_settings(KIOSK_ENABLED=True, KIOSK_PORT=8100, KIOSK_TOKEN="secret123")
    def test_kiosk_readonly_restriction(self) -> None:
        # Non-GET requests on kiosk port should be forbidden
        response = self.client.post(
            "/api/plans/",
            data="{}",
            content_type="application/json",
            SERVER_PORT="8100",
            HTTP_X_KIOSK_TOKEN="secret123",
        )
        assert response.status_code == 403

    @override_settings(KIOSK_ENABLED=True, KIOSK_PORT=8100, KIOSK_TOKEN="secret123")
    def test_kiosk_valid_token(self) -> None:
        response = self.client.get("/kiosk/", SERVER_PORT="8100", HTTP_X_KIOSK_TOKEN="secret123")
        assert response.status_code == 200
        assert b"Security Hawk" in response.content

    def test_spa_view_ingress_injection(self) -> None:
        response = self.client.get("/", HTTP_X_INGRESS_PATH="/api/hassio_ingress/token123")
        assert response.status_code == 200
        assert b'window.__INGRESS_PATH__ = "/api/hassio_ingress/token123"' in response.content

    def test_plan_crud_lifecycle(self) -> None:
        # Create plan
        res_create = self.client.post(
            "/api/plans/",
            data=json.dumps({"name": "Test Site Plan"}),
            content_type="application/json",
        )
        assert res_create.status_code == 201
        plan_id = res_create.json()["id"]

        # Get plan
        res_get = self.client.get(f"/api/plans/{plan_id}/")
        assert res_get.status_code == 200
        assert res_get.json()["plan"]["name"] == "Test Site Plan"

        # Update plan
        plan_data = res_get.json()["plan"]
        plan_data["name"] = "Updated Site Plan"
        res_update = self.client.put(
            f"/api/plans/{plan_id}/",
            data=json.dumps(plan_data),
            content_type="application/json",
        )
        assert res_update.status_code == 200

        # List versions
        res_versions = self.client.get(f"/api/plans/{plan_id}/versions/")
        assert res_versions.status_code == 200

        # Delete plan
        res_delete = self.client.delete(f"/api/plans/{plan_id}/")
        assert res_delete.status_code == 200

        # Verify 404
        assert self.client.get(f"/api/plans/{plan_id}/").status_code == 404

    def test_ingress_middleware_ip_filter(self) -> None:
        # Ingress port 8099 with non-ingress IP should be 403
        res = self.client.get("/", SERVER_PORT="8099", REMOTE_ADDR="192.168.1.50")
        assert res.status_code == 403

        # Ingress port 8099 with authorized IP 172.30.32.2 should be allowed
        res_ok = self.client.get("/", SERVER_PORT="8099", REMOTE_ADDR="172.30.32.2")
        assert res_ok.status_code == 200
