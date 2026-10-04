"""REST API views for plan management.

Endpoints:
    GET    /api/plans/                       — list all plans
    POST   /api/plans/                       — create a new plan
    GET    /api/plans/<plan_id>/              — get a plan
    PUT    /api/plans/<plan_id>/              — update a plan (autosave)
    DELETE /api/plans/<plan_id>/              — delete a plan
    POST   /api/plans/<plan_id>/assets/       — upload a background asset
    GET    /api/plans/<plan_id>/versions/      — list saved versions
    POST   /api/plans/<plan_id>/restore/       — restore a version
"""

from __future__ import annotations

import io
import json
import logging
import os
import uuid
import zipfile

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.utils.text import slugify
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from plans.migrations import migrate_plan_data
from plans.sanitize import sanitize_svg
from plans.schema import default_plan, new_plan_id, validate_plan
from plans.storage import PlanStorage

logger = logging.getLogger(__name__)

# Singleton storage instance
_storage = PlanStorage(
    plans_dir=str(settings.PLANS_DIR),
    versions_dir=str(settings.VERSIONS_DIR),
    max_versions=settings.MAX_VERSIONS,
)


def get_storage() -> PlanStorage:
    return _storage


@csrf_exempt
@require_http_methods(["GET", "POST"])
def plans_collection(request):
    """Handle collection-level plan operations: GET (list) and POST (create)."""
    if request.method == "POST":
        return create_plan(request)
    return list_plans(request)


@csrf_exempt
@require_http_methods(["GET", "PUT", "DELETE"])
def plan_detail(request, plan_id):
    """Handle single-plan operations: GET, PUT (update/autosave), and DELETE."""
    if request.method == "PUT":
        return update_plan(request, plan_id)
    elif request.method == "DELETE":
        return delete_plan(request, plan_id)
    return get_plan(request, plan_id)


@require_GET
def list_plans(request):
    """List all plans with summary info."""
    plans = get_storage().list_plans()
    return JsonResponse({"plans": plans})


@csrf_exempt
@require_POST
def create_plan(request):
    """Create a new empty plan."""
    try:
        body = json.loads(request.body) if request.body else {}
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    name = body.get("name", "New Plan")
    plan_id = new_plan_id()
    plan = default_plan(name)

    get_storage().save(plan_id, plan)

    return JsonResponse({"id": plan_id, "plan": plan}, status=201)


@require_GET
def get_plan(request, plan_id):
    """Get a plan by ID."""
    plan = get_storage().load(plan_id)
    if plan is None:
        return JsonResponse({"error": "Plan not found"}, status=404)
    return JsonResponse({"id": plan_id, "plan": plan})


@csrf_exempt
@require_http_methods(["PUT"])
def update_plan(request, plan_id):
    """Update (autosave) a plan. Expects the full plan JSON in the body."""
    existing = get_storage().load(plan_id)
    if existing is None:
        return JsonResponse({"error": "Plan not found"}, status=404)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    get_storage().save(plan_id, data)

    # Update the state manager with the new set of placed entity IDs
    _update_placed_entities(plan_id, data)

    return JsonResponse({"status": "saved"})


@csrf_exempt
@require_http_methods(["DELETE"])
def delete_plan(request, plan_id):
    """Delete a plan."""
    if get_storage().delete(plan_id):
        return JsonResponse({"status": "deleted"})
    return JsonResponse({"error": "Plan not found"}, status=404)


@csrf_exempt
@require_POST
def upload_asset(request, plan_id):
    """Upload a background image or SVG for a plan.

    Accepts multipart/form-data with a 'file' field.
    SVG files are sanitized before storage.
    """
    if "file" not in request.FILES:
        return JsonResponse({"error": "No file uploaded"}, status=400)

    uploaded = request.FILES["file"]
    filename = uploaded.name
    ext = os.path.splitext(filename)[1].lower()

    # Validate file type
    allowed_extensions = {".svg", ".png", ".jpg", ".jpeg", ".webp"}
    if ext not in allowed_extensions:
        return JsonResponse(
            {"error": f"Unsupported file type: {ext}. Allowed: {', '.join(allowed_extensions)}"},
            status=400,
        )

    # Read file content
    content = uploaded.read()

    # Sanitize SVG files
    if ext == ".svg":
        try:
            content = sanitize_svg(content)
        except Exception as e:
            logger.error("SVG sanitization failed: %s", e)
            return JsonResponse({"error": "Invalid or dangerous SVG file"}, status=400)

    # Generate a unique filename to avoid collisions
    asset_id = uuid.uuid4().hex[:12]
    safe_name = f"{asset_id}{ext}"

    # Save to assets directory
    plan_assets_dir = os.path.join(str(settings.ASSETS_DIR), plan_id)
    os.makedirs(plan_assets_dir, exist_ok=True)
    asset_path = os.path.join(plan_assets_dir, safe_name)

    with open(asset_path, "wb") as f:
        f.write(content)

    logger.info("Uploaded asset %s for plan %s (%d bytes)", safe_name, plan_id, len(content))

    return JsonResponse(
        {
            "asset_id": asset_id,
            "filename": safe_name,
            "original_name": filename,
            "url": f"/assets/{plan_id}/{safe_name}",
            "size": len(content),
        },
        status=201,
    )


@require_GET
def list_versions(request, plan_id):
    """List available version snapshots for a plan."""
    versions = get_storage().list_versions(plan_id)
    return JsonResponse({"versions": versions})


@csrf_exempt
@require_POST
def restore_version(request, plan_id):
    """Restore a plan from a version snapshot."""
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    version_filename = body.get("version")
    if not version_filename:
        return JsonResponse({"error": "Missing 'version' field"}, status=400)

    try:
        plan = get_storage().restore_version(plan_id, version_filename)
    except FileNotFoundError:
        return JsonResponse({"error": "Version not found"}, status=404)

    _update_placed_entities(plan_id, plan)

    return JsonResponse({"status": "restored", "plan": plan})


def _update_placed_entities(plan_id: str, plan_data: dict) -> None:
    """Extract all placed entity IDs from a plan and update the state manager."""
    from live.state_manager import state_manager

    entity_ids = set()

    # Overview endpoints
    overview = plan_data.get("overview", {})
    for ep in overview.get("endpoints", []):
        entity_ids.add(ep["entity_id"])
        entity_ids.update(ep.get("companions", []))

    # Building floor endpoints
    for building in plan_data.get("buildings", []):
        for floor in building.get("floors", []):
            for ep in floor.get("endpoints", []):
                entity_ids.add(ep["entity_id"])
                entity_ids.update(ep.get("companions", []))

    state_manager.load_placed_entities(plan_id, entity_ids)


@require_GET
def export_plan(request, plan_id):
    """Export a plan as a downloadable JSON file attachment."""
    plan = get_storage().load(plan_id)
    if not plan:
        return JsonResponse({"error": "Plan not found"}, status=404)

    safe_name = slugify(plan.get("name", plan_id)) or "floorplan"
    filename = f"{safe_name}_plan.json"

    response = HttpResponse(
        json.dumps(plan, indent=2),
        content_type="application/json",
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@require_GET
def export_bundle(request, plan_id):
    """Export a complete plan bundle (.zip) containing plan.json and background assets (Spec §Import and export)."""
    plan = get_storage().load(plan_id)
    if not plan:
        return JsonResponse({"error": "Plan not found"}, status=404)

    safe_name = slugify(plan.get("name", plan_id)) or "floorplan"
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. Write plan.json
        zf.writestr("plan.json", json.dumps(plan, indent=2))

        # 2. Write assets if they exist
        plan_assets_dir = os.path.join(str(settings.ASSETS_DIR), plan_id)
        if os.path.exists(plan_assets_dir):
            for fname in os.listdir(plan_assets_dir):
                fpath = os.path.join(plan_assets_dir, fname)
                if os.path.isfile(fpath):
                    zf.write(fpath, arcname=f"assets/{fname}")

    response = HttpResponse(zip_buffer.getvalue(), content_type="application/zip")
    response["Content-Disposition"] = f'attachment; filename="{safe_name}_bundle.zip"'
    return response


@csrf_exempt
@require_POST
def import_plan(request, plan_id=None):
    """Import a plan from an uploaded JSON file, ZIP bundle, or request body."""
    # Check for file upload or body payload
    if request.FILES and "file" in request.FILES:
        uploaded_file = request.FILES["file"]
        is_zip = uploaded_file.name.endswith(".zip")
        content_prefix = uploaded_file.read(4)
        uploaded_file.seek(0)

        # Handle ZIP bundle (.zip or zip magic bytes)
        if is_zip or content_prefix.startswith(b"PK\x03\x04"):
            try:
                zip_bytes = uploaded_file.read()
                zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
                plan_json_name = None
                for name in zf.namelist():
                    if name == "plan.json" or name.endswith("/plan.json") or (name.endswith(".json") and not plan_json_name):
                        plan_json_name = name

                if not plan_json_name:
                    return JsonResponse({"error": "No plan.json found in ZIP bundle"}, status=400)

                raw_json = zf.read(plan_json_name).decode("utf-8")
                data = json.loads(raw_json)

                # Migrate schema if older version
                migrated_data, was_migrated = migrate_plan_data(data)
                errors = validate_plan(migrated_data)
                if errors:
                    return JsonResponse({"error": "Validation failed", "details": errors}, status=400)

                target_id = plan_id or data.get("id") or str(uuid.uuid4())[:8]

                # Extract assets safely into plan_assets_dir
                plan_assets_dir = os.path.join(str(settings.ASSETS_DIR), target_id)
                os.makedirs(plan_assets_dir, exist_ok=True)
                for member in zf.namelist():
                    if member.startswith("assets/") and not member.endswith("/"):
                        filename = os.path.basename(member)
                        if filename:
                            out_path = os.path.join(plan_assets_dir, filename)
                            with open(out_path, "wb") as out_f:
                                out_f.write(zf.read(member))

                get_storage().save(target_id, migrated_data)
                _update_placed_entities(target_id, migrated_data)

                logger.info("Imported plan bundle %s (migrated: %s)", target_id, was_migrated)
                return JsonResponse(
                    {
                        "status": "imported",
                        "plan_id": target_id,
                        "plan": migrated_data,
                        "migrated": was_migrated,
                        "is_bundle": True,
                    }
                )
            except Exception as e:
                logger.error("Failed to extract ZIP bundle: %s", e)
                return JsonResponse({"error": f"Failed to extract ZIP bundle: {e}"}, status=400)

        # Handle regular JSON file
        try:
            raw_content = uploaded_file.read().decode("utf-8")
            data = json.loads(raw_content)
        except Exception as e:
            return JsonResponse({"error": f"Failed to read uploaded JSON file: {e}"}, status=400)
    else:
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON body"}, status=400)

    if not isinstance(data, dict):
        return JsonResponse({"error": "Plan payload must be a JSON object"}, status=400)

    # Automatically migrate schema if older version
    migrated_data, was_migrated = migrate_plan_data(data)

    errors = validate_plan(migrated_data)
    if errors:
        return JsonResponse({"error": "Validation failed", "details": errors}, status=400)

    # Determine plan ID (use provided, or extract from data, or generate new)
    target_id = plan_id or data.get("id") or str(uuid.uuid4())[:8]

    # Save to storage (will automatically snapshot previous version if existing)
    get_storage().save(target_id, migrated_data)
    _update_placed_entities(target_id, migrated_data)

    logger.info("Imported plan %s (migrated: %s)", target_id, was_migrated)
    return JsonResponse(
        {
            "status": "imported",
            "plan_id": target_id,
            "plan": migrated_data,
            "migrated": was_migrated,
            "is_bundle": False,
        }
    )
