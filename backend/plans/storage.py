"""JSON file storage for plans with rolling version history.

Plans are stored as JSON files in DATA_DIR/plans/. Before each save,
the current version is copied to DATA_DIR/versions/<plan_id>/ with a
timestamp. The oldest versions are pruned to keep at most MAX_VERSIONS.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
from datetime import UTC, datetime

logger = logging.getLogger(__name__)


class PlanStorage:
    """Read/write plans as JSON files with automatic versioning."""

    def __init__(self, plans_dir: str, versions_dir: str, max_versions: int = 20):
        self.plans_dir = plans_dir
        self.versions_dir = versions_dir
        self.max_versions = max_versions
        os.makedirs(plans_dir, exist_ok=True)
        os.makedirs(versions_dir, exist_ok=True)

    def _plan_path(self, plan_id: str) -> str:
        # Sanitize plan_id to prevent path traversal
        safe_id = plan_id.replace("/", "_").replace("..", "_")
        return os.path.join(self.plans_dir, f"{safe_id}.json")

    def list_plans(self) -> list[dict]:
        """Return a list of plan summaries (id, name, modified time)."""
        plans = []
        for filename in os.listdir(self.plans_dir):
            if not filename.endswith(".json"):
                continue
            plan_id = filename[:-5]
            path = os.path.join(self.plans_dir, filename)
            try:
                with open(path) as f:
                    data = json.load(f)
                plans.append(
                    {
                        "id": plan_id,
                        "name": data.get("name", plan_id),
                        "schema_version": data.get("schema_version", 1),
                        "modified": os.path.getmtime(path),
                    }
                )
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Skipping corrupt plan %s: %s", filename, e)
        return sorted(plans, key=lambda p: p["modified"], reverse=True)

    def load(self, plan_id: str) -> dict | None:
        """Load a plan by ID. Automatically migrates older schema versions."""
        from plans.migrations import migrate_plan_data

        path = self._plan_path(plan_id)
        if not os.path.exists(path):
            return None
        with open(path) as f:
            data = json.load(f)

        migrated_data, was_modified = migrate_plan_data(data)
        if was_modified:
            # Silently persist the upgraded schema
            with open(path, "w") as f:
                json.dump(migrated_data, f, indent=2)

        return migrated_data

    def save(self, plan_id: str, data: dict) -> None:
        """Save a plan, creating a version snapshot of the previous state."""
        from plans.migrations import migrate_plan_data

        path = self._plan_path(plan_id)
        migrated_data, _ = migrate_plan_data(data)

        # Snapshot current version before overwriting
        if os.path.exists(path):
            self._save_version(plan_id, path)

        with open(path, "w") as f:
            json.dump(migrated_data, f, indent=2)

        logger.info("Saved plan %s", plan_id)

    def delete(self, plan_id: str) -> bool:
        """Delete a plan file. Returns True if deleted."""
        path = self._plan_path(plan_id)
        if os.path.exists(path):
            os.remove(path)
            return True
        return False

    def _save_version(self, plan_id: str, current_path: str) -> None:
        """Copy the current plan file into the version history directory."""
        ver_dir = os.path.join(self.versions_dir, plan_id)
        os.makedirs(ver_dir, exist_ok=True)

        ts = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S_%f")
        ver_path = os.path.join(ver_dir, f"{plan_id}_{ts}.json")
        shutil.copy2(current_path, ver_path)

        # Prune old versions beyond the limit
        versions = sorted(os.listdir(ver_dir))
        while len(versions) > self.max_versions:
            oldest = versions.pop(0)
            os.remove(os.path.join(ver_dir, oldest))
            logger.debug("Pruned old version %s", oldest)

    def list_versions(self, plan_id: str) -> list[dict]:
        """List available versions for a plan."""
        ver_dir = os.path.join(self.versions_dir, plan_id)
        if not os.path.exists(ver_dir):
            return []
        versions = []
        for filename in sorted(os.listdir(ver_dir)):
            path = os.path.join(ver_dir, filename)
            versions.append(
                {
                    "filename": filename,
                    "modified": os.path.getmtime(path),
                    "size": os.path.getsize(path),
                }
            )
        return versions

    def restore_version(self, plan_id: str, version_filename: str) -> dict:
        """Restore a plan from a version snapshot.

        The current plan is versioned first, then the snapshot replaces it.
        Returns the restored plan data.
        """
        ver_path = os.path.join(self.versions_dir, plan_id, version_filename)
        if not os.path.exists(ver_path):
            raise FileNotFoundError(f"Version not found: {version_filename}")

        # Save current state as a version before restoring
        current = self._plan_path(plan_id)
        if os.path.exists(current):
            self._save_version(plan_id, current)

        shutil.copy2(ver_path, current)
        logger.info("Restored plan %s from version %s", plan_id, version_filename)

        with open(current) as f:
            return json.load(f)
