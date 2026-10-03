"""API views for managing rules and testing synthetic sensors."""

from __future__ import annotations

import json

from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from rules.engine import rules_engine
from rules.storage import rules_storage


@csrf_exempt
def list_or_create_rules(request: HttpRequest) -> JsonResponse:
    """GET /api/rules/ or POST /api/rules/"""
    if request.method == "GET":
        rules = rules_storage.list_rules()
        return JsonResponse({"rules": rules})

    if request.method == "POST":
        try:
            body = json.loads(request.body.decode("utf-8"))
        except Exception:
            return JsonResponse({"error": "Invalid JSON body"}, status=400)

        saved = rules_storage.create_or_update(body)
        return JsonResponse({"status": "ok", "rule": saved}, status=201)

    return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
def rule_detail(request: HttpRequest, rule_id: str) -> JsonResponse:
    """GET, PUT, or DELETE /api/rules/<rule_id>/"""
    rule = rules_storage.get_rule(rule_id)
    if not rule and request.method != "PUT":
        return JsonResponse({"error": "Rule not found"}, status=404)

    if request.method == "GET":
        return JsonResponse({"rule": rule})

    if request.method == "PUT":
        try:
            body = json.loads(request.body.decode("utf-8"))
        except Exception:
            return JsonResponse({"error": "Invalid JSON body"}, status=400)

        body["id"] = rule_id
        saved = rules_storage.create_or_update(body)
        return JsonResponse({"status": "ok", "rule": saved})

    if request.method == "DELETE":
        deleted = rules_storage.delete(rule_id)
        if deleted:
            return JsonResponse({"status": "deleted", "id": rule_id})
        return JsonResponse({"error": "Rule not found"}, status=404)

    return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
async def test_rule(request: HttpRequest, rule_id: str) -> JsonResponse:
    """POST /api/rules/<rule_id>/test/ to execute a rule on-demand."""
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    rule = rules_storage.get_rule(rule_id)
    if not rule:
        return JsonResponse({"error": "Rule not found"}, status=404)

    conditions = rule.get("conditions", [])
    test_entities = [c.get("entity_id") for c in conditions if c.get("entity_id")] or [
        "manual_test"
    ]
    await rules_engine.execute_rule(rule, test_entities)

    return JsonResponse(
        {
            "status": "triggered",
            "rule_id": rule_id,
            "output_entity_id": rule.get("output_entity_id"),
            "triggered_by": test_entities,
        }
    )


def list_action_plugins(request: HttpRequest) -> JsonResponse:
    """GET /api/rules/action-plugins/ to list available expandable action plugins."""
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    from rules.actions import action_registry

    plugins = action_registry.list_plugins()
    return JsonResponse({"plugins": plugins})


def worker_status(request: HttpRequest) -> JsonResponse:
    """GET /api/rules/worker-status/ to get runtime stats for the background rule worker."""
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    from rules.worker import rule_worker

    return JsonResponse(rule_worker.get_stats())
