from django.http import JsonResponse
from django.urls import include, path, re_path
from django.views.static import serve

from securityhawk import settings


def spa_view(request, *args, **kwargs):
    """Serve the Vue SPA index.html for all non-API/WS routes."""
    import os

    index_path = os.path.join(settings.BASE_DIR, "static", "frontend", "index.html")
    try:
        with open(index_path) as f:
            content = f.read()
        # Inject the ingress path so the Vue app can construct correct URLs
        ingress_path = getattr(request, "ingress_path", "")
        content = content.replace(
            "</head>",
            f'<script>window.__INGRESS_PATH__ = "{ingress_path}";</script></head>',
        )
        from django.http import HttpResponse

        return HttpResponse(content, content_type="text/html")
    except FileNotFoundError:
        return JsonResponse(
            {"error": "Frontend not built. Run 'npm run build' in frontend/."},
            status=500,
        )


def health_check(request):
    """Simple health check endpoint."""
    return JsonResponse({"status": "ok", "version": "0.2.0"})


urlpatterns = [
    # Health check
    path("api/health/", health_check),
    # API routes
    path("api/", include("plans.urls")),
    path("api/", include("ha.urls")),
    path("api/", include("rules.urls")),
    path("api/", include("settings_mgr.urls")),
    # Serve uploaded assets from DATA_DIR
    path(
        "assets/<path:path>",
        serve,
        {"document_root": settings.ASSETS_DIR},
    ),
    # Vue SPA catch-all (must be last)
    re_path(r"^(?!api/|ws/|static/|assets/).*$", spa_view),
]
