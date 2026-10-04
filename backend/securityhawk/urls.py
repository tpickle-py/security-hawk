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


def asset_view(request, path):
    """Serve built frontend assets (JS/CSS/fonts) or user-uploaded plan assets."""
    # 1. Built frontend assets in static/frontend/assets
    frontend_assets_dir = settings.BASE_DIR / "static" / "frontend" / "assets"
    if (frontend_assets_dir / path).is_file():
        return serve(request, path, document_root=str(frontend_assets_dir))

    # Also check collected_static if present
    if settings.STATIC_ROOT:
        collected_frontend = settings.STATIC_ROOT / "frontend" / "assets"
        if (collected_frontend / path).is_file():
            return serve(request, path, document_root=str(collected_frontend))

    # 2. User-uploaded plan assets in DATA_DIR / assets
    if (settings.ASSETS_DIR / path).is_file():
        return serve(request, path, document_root=str(settings.ASSETS_DIR))

    from django.http import Http404
    raise Http404(f"Asset '{path}' not found")


def static_view(request, path):
    """Serve collected or local static files."""
    if settings.STATIC_ROOT and (settings.STATIC_ROOT / path).is_file():
        return serve(request, path, document_root=str(settings.STATIC_ROOT))

    static_dir = settings.BASE_DIR / "static"
    if (static_dir / path).is_file():
        return serve(request, path, document_root=str(static_dir))

    from django.http import Http404
    raise Http404(f"Static file '{path}' not found")


urlpatterns = [
    # Health check
    path("api/health/", health_check),
    # API routes
    path("api/", include("plans.urls")),
    path("api/", include("ha.urls")),
    path("api/", include("rules.urls")),
    path("api/", include("settings_mgr.urls")),
    path("api/", include("kiosk.urls")),
    # Serve assets (frontend JS/CSS/fonts or user uploaded plan assets)
    path("assets/<path:path>", asset_view, name="assets"),
    # Serve static files
    path("static/<path:path>", static_view, name="static"),
    # Vue SPA catch-all (must be last)
    re_path(r"^(?!api/|ws/|static/|assets/).*$", spa_view),
]
