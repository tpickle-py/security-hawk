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

        if str(server_port) == "8099":
            # Ingress port — restrict to HA proxy IP
            remote_ip = request.META.get("REMOTE_ADDR", "")
            if remote_ip != INGRESS_IP:
                logger.warning("Rejected non-ingress connection from %s on port 8099", remote_ip)
                return HttpResponseForbidden("Forbidden")

        # Extract ingress path for URL generation in templates/API responses
        ingress_path = request.META.get("HTTP_X_INGRESS_PATH", "")
        request.ingress_path = ingress_path

        return self.get_response(request)
