"""Middleware for kiosk authentication and read-only enforcement."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django.conf import settings
from django.http import HttpResponseForbidden

if TYPE_CHECKING:
    from collections.abc import Callable

    from django.http import HttpRequest, HttpResponse

logger = logging.getLogger(__name__)


class KioskTokenMiddleware:
    """Enforce token authentication and read-only restrictions on the kiosk port/view.

    - Rejects access on kiosk port if KIOSK_ENABLED is false.
    - Validates ?token= query parameter, X-Kiosk-Token header, or Bearer token if KIOSK_TOKEN is set.
    - Restricts kiosk requests to read-only HTTP methods (GET, HEAD, OPTIONS).
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        server_port = str(request.META.get("SERVER_PORT", ""))
        kiosk_port = str(getattr(settings, "KIOSK_PORT", "8100"))
        is_kiosk_port = server_port == kiosk_port
        is_kiosk_path = request.path.startswith("/kiosk")

        if is_kiosk_port or is_kiosk_path:
            # Check if kiosk mode is enabled
            if not getattr(settings, "KIOSK_ENABLED", False) and is_kiosk_port:
                return HttpResponseForbidden("Kiosk mode is disabled.")

            # Kiosk is strictly read-only
            if request.method not in ("GET", "HEAD", "OPTIONS"):
                return HttpResponseForbidden("Kiosk mode is read-only.")

            # Check kiosk token if configured
            expected_token = getattr(settings, "KIOSK_TOKEN", "")
            if expected_token:
                # 1. Query parameter
                provided_token = request.GET.get("token")
                # 2. Custom header
                if not provided_token:
                    provided_token = request.META.get("HTTP_X_KIOSK_TOKEN")
                # 3. Authorization: Bearer <token>
                if not provided_token:
                    auth_header = request.META.get("HTTP_AUTHORIZATION", "")
                    if auth_header.startswith("Bearer "):
                        provided_token = auth_header.split(" ", 1)[1].strip()

                if not provided_token or provided_token != expected_token:
                    logger.warning(
                        "Unauthorized kiosk request from %s", request.META.get("REMOTE_ADDR")
                    )
                    return HttpResponseForbidden("Invalid or missing kiosk token.")

            request.is_kiosk = True  # type: ignore[attr-defined]

        return self.get_response(request)
