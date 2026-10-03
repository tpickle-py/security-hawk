"""Tests for plan storage and rolling versioning."""

from __future__ import annotations

from pathlib import Path

import pytest

from plans.storage import PlanStorage


@pytest.fixture
def storage(tmp_path: Path) -> PlanStorage:
    plans_dir = tmp_path / "plans"
    versions_dir = tmp_path / "versions"
    return PlanStorage(str(plans_dir), str(versions_dir), max_versions=3)


def test_save_and_load(storage: PlanStorage) -> None:
    data = {"name": "Test Floor", "endpoints": []}
    storage.save("plan_1", data)

    loaded = storage.load("plan_1")
    assert loaded is not None
    assert loaded["name"] == "Test Floor"
    assert loaded["schema_version"] == 2
    assert "overview" in loaded


def test_load_nonexistent(storage: PlanStorage) -> None:
    assert storage.load("does_not_exist") is None


def test_versioning_and_pruning(storage: PlanStorage, tmp_path: Path) -> None:
    # Initial save creates the file
    storage.save("p1", {"v": 1})
    assert len(storage.list_versions("p1")) == 0

    # Subsequent saves create versions
    storage.save("p1", {"v": 2})
    assert len(storage.list_versions("p1")) == 1

    storage.save("p1", {"v": 3})
    assert len(storage.list_versions("p1")) == 2

    storage.save("p1", {"v": 4})
    assert len(storage.list_versions("p1")) == 3

    # Exceeding max_versions (3) prunes the oldest version
    storage.save("p1", {"v": 5})
    versions = storage.list_versions("p1")
    assert len(versions) == 3

    # Restore the most recent version
    restored = storage.restore_version("p1", versions[-1]["filename"])
    assert restored["v"] == 4


def test_list_and_delete(storage: PlanStorage) -> None:
    storage.save("p1", {"name": "First Plan"})
    storage.save("p2", {"name": "Second Plan"})

    plans = storage.list_plans()
    assert len(plans) == 2
    ids = {p["id"] for p in plans}
    assert ids == {"p1", "p2"}

    # Delete
    assert storage.delete("p1") is True
    assert storage.load("p1") is None
    assert storage.delete("p1") is False
