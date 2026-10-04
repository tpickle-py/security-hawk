"""Views for kiosk status and active viewer telemetry."""

from __future__ import annotations

from django.conf import settings
from django.http import HttpRequest, JsonResponse

from live.consumers import connection_tracker


def kiosk_status(request: HttpRequest) -> JsonResponse:
    """GET /api/kiosk/status/

    Returns current kiosk configuration and active connected viewer statistics.
    """
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    stats = connection_tracker.get_stats()
    return JsonResponse(
        {
            "kiosk_enabled": bool(getattr(settings, "KIOSK_ENABLED", False)),
            "kiosk_port": int(getattr(settings, "KIOSK_PORT", 8100)),
            "kiosk_token": str(getattr(settings, "KIOSK_TOKEN", "")),
            "active_viewers": stats,
        }
    )
