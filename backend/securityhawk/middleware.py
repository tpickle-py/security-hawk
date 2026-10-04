import logging

from django.http import HttpResponseForbidden

logger = logging.getLogger(__name__)

INGRESS_IP = "172.30.32.2"


class IngressMiddleware:
    """Enforce ingress security and extract X-Ingress-Path.

    On port 8099 (ingress), only accept connections from 172.30.32.2
    as required by the HA app developer docs. Extract X-Ingress-Path
    for the frontend to construct correct URLs behind the ingress proxy.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Determine which port we're serving on
        server_port = request.META.get("SERVER_PORT", "")

        # Extract ingress path for URL generation in templates/API responses
        ingress_path = request.META.get("HTTP_X_INGRESS_PATH", "")
        request.ingress_path = ingress_path

        if str(server_port) == "8099":
            # Ingress port — allow if connecting from HA proxy IP, local container network,
            # or if carrying the Home Assistant X-Ingress-Path proxy header
            remote_ip = request.META.get("REMOTE_ADDR", "")
            is_ingress_origin = (
                remote_ip == INGRESS_IP
                or remote_ip.startswith("172.30.")
                or remote_ip == "127.0.0.1"
                or bool(ingress_path)
            )
            if not is_ingress_origin:
                logger.warning(
                    "Rejected non-ingress connection from %s on port 8099 (no X-Ingress-Path header)",
                    remote_ip,
                )
                return HttpResponseForbidden("Forbidden")

        return self.get_response(request)
