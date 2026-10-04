"""REST API views for Home Assistant entity and area data.

Endpoints:
    GET  /api/entities/                     — search HA entities (friendly name, ID, domain, area)
    GET  /api/entities/lookup/              — lookup entity by exact/case-insensitive friendly name
    GET  /api/entities/<entity_id>/         — get single entity detail + state
    POST /api/entities/<entity_id>/area/    — designate area for entity
    GET  /api/areas/                        — get all rooms/areas and unassigned entity counts
    GET  /api/camera/<entity_id>/           — proxy camera snapshot
"""

from __future__ import annotations

import asyncio
import json
import logging
import urllib.request

from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods

from ha.client import HARestClient
from ha.registry import entity_registry

logger = logging.getLogger(__name__)


@require_GET
def search_entities(request):
    """Search HA entities for the entity picker.

    Query params:
        q: search query (matches friendly name, entity_id, or area_name)
        domain: filter by domain (e.g., binary_sensor, camera)
        area_id: filter by specific area
        unassigned_area: "true" to only return entities without an assigned area
        limit: max results (default 50)
    """
    query = request.GET.get("q", "")
    domain = request.GET.get("domain", "")
    area_id = request.GET.get("area_id", "")
    unassigned_only = request.GET.get("unassigned_area", "").lower() in ("true", "1", "yes")
    limit = min(int(request.GET.get("limit", "50")), 200)

    results = entity_registry.search(
        query=query,
        domain=domain,
        limit=limit,
        area_id=area_id,
        unassigned_only=unassigned_only,
    )
    return JsonResponse({"entities": results})


@require_GET
def lookup_entity_by_friendly_name(request):
    """Look up an entity by its friendly name."""
    name = request.GET.get("name", "")
    if not name:
        return JsonResponse({"error": "Query param 'name' is required"}, status=400)

    entity = entity_registry.lookup_by_friendly_name(name)
    if entity is None:
        return JsonResponse({"error": "No entity found with that friendly name"}, status=404)

    return JsonResponse({"entity": entity})


@require_GET
def list_areas(request):
    """Return all Home Assistant areas/rooms and count unassigned entities."""
    areas = entity_registry.get_areas()
    all_entities = entity_registry.search(limit=2000)
    unassigned_count = sum(1 for e in all_entities if not e.get("area_id"))

    # Calculate entity counts per area
    area_counts = {}
    for e in all_entities:
        aid = e.get("area_id")
        if aid:
            area_counts[aid] = area_counts.get(aid, 0) + 1

    areas_with_counts = [
        {
            **a,
            "entity_count": area_counts.get(a["area_id"], 0),
        }
        for a in areas
    ]

    return JsonResponse(
        {
            "areas": areas_with_counts,
            "total_areas": len(areas),
            "unassigned_entities_count": unassigned_count,
        }
    )


@csrf_exempt
@require_http_methods(["POST"])
def designate_entity_area(request, entity_id):
    """Designate or change the room/area for an entity."""
    try:
        body = json.loads(request.body) if request.body else {}
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    area_id = body.get("area_id")  # Can be string or None to unassign
    success = entity_registry.set_entity_area(entity_id, area_id)
    if not success:
        return JsonResponse({"error": "Entity not found in registry"}, status=404)

    logger.info("Designated area %s for entity %s", area_id, entity_id)
    return JsonResponse({"status": "designated", "entity_id": entity_id, "area_id": area_id})


@require_GET
def get_entity(request, entity_id):
    """Get detailed entity info + current state."""
    entity = entity_registry.get_entity(entity_id)
    if entity is None:
        return JsonResponse({"error": "Entity not found"}, status=404)

    state = entity_registry.get_state(entity_id)
    return JsonResponse(
        {
            "entity": entity,
            "state": state,
        }
    )


@require_GET
def camera_snapshot(request, entity_id):
    """Proxy a camera snapshot from HA.

    Only allows access to camera entities to prevent arbitrary API proxying.
    """
    if not entity_id.startswith("camera."):
        return JsonResponse({"error": "Not a camera entity"}, status=400)

    client = HARestClient()
    try:
        image_bytes, content_type = asyncio.get_event_loop().run_until_complete(
            client.get_camera_snapshot(entity_id)
        )
    except Exception as e:
        logger.error("Failed to fetch camera snapshot for %s: %s", entity_id, e)
        return JsonResponse({"error": "Failed to fetch snapshot"}, status=502)

    return HttpResponse(image_bytes, content_type=content_type)


@require_GET
def camera_stream(request, entity_id):
    """Proxy live MJPEG camera stream from Home Assistant."""
    if not entity_id.startswith("camera."):
        return JsonResponse({"error": "Not a camera entity"}, status=400)

    client = HARestClient()
    url = f"{client.base_url}/camera_proxy_stream/{entity_id}"
    req = urllib.request.Request(url, headers=client.headers)

    try:
        remote_stream = urllib.request.urlopen(req, timeout=10)
        content_type = remote_stream.headers.get("Content-Type", "multipart/x-mixed-replace; boundary=--frame")

        def stream_chunks():
            try:
                while True:
                    chunk = remote_stream.read(4096)
                    if not chunk:
                        break
                    yield chunk
            except Exception:
                pass
            finally:
                remote_stream.close()

        return StreamingHttpResponse(stream_chunks(), content_type=content_type)
    except Exception as e:
        logger.debug("Failed to stream camera %s: %s, falling back to snapshot", entity_id, e)
        return camera_snapshot(request, entity_id)
