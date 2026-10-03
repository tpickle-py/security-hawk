import { defineStore } from "pinia";
import { ref, computed } from "vue";
import type { Site, Floor, Endpoint, Scale, BackgroundAsset, SubArea, Shape, WallOpening, WallGeometry } from "@/types/plan";
import { api } from "@/services/api";
import { useHistoryStore } from "@/stores/historyStore";

export const usePlanStore = defineStore("plan", () => {
  const currentPlanId = ref<string | null>(null);
  const site = ref<Site | null>(null);
  const currentBuildingId = ref<string | null>(null); // null = overview
  const currentFloorId = ref<string | null>(null);
  const isLoading = ref(false);
  const isSaving = ref(false);
  const lastSavedAt = ref<Date | null>(null);
  const error = ref<string | null>(null);

  // Computed active floor / view
  const isOverview = computed(() => currentBuildingId.value === null);

  const currentBuilding = computed(() => {
    if (!site.value || !currentBuildingId.value) return null;
    return site.value.buildings.find((b) => b.id === currentBuildingId.value) || null;
  });

  const currentFloor = computed<Floor | null>(() => {
    if (!site.value) return null;
    if (isOverview.value) {
      // overview is a FloorLike, cast for interface uniformity
      return {
        ...site.value.overview,
        shapes: [],
      } as Floor;
    }
    const b = currentBuilding.value;
    if (!b) return null;
    return b.floors.find((f) => f.id === currentFloorId.value) || b.floors[0] || null;
  });

  const currentEndpoints = computed<Endpoint[]>(() => {
    return currentFloor.value?.endpoints || [];
  });

  async function loadPlan(planId: string) {
    isLoading.value = true;
    error.value = null;
    try {
      const data = await api.getPlan(planId);
      currentPlanId.value = data.id;
      site.value = data.plan;

      // Select overview or first floor
      currentBuildingId.value = null;
      currentFloorId.value = null;
      useHistoryStore().clear();
    } catch (e: any) {
      error.value = e.message || "Failed to load plan";
      throw e;
    } finally {
      isLoading.value = false;
    }
  }

  let saveTimeout: number | null = null;

  function snapshotBeforeMutation() {
    if (site.value) {
      useHistoryStore().pushState(site.value);
    }
  }

  function markDirtyAndAutosave() {
    if (saveTimeout) clearTimeout(saveTimeout);
    saveTimeout = window.setTimeout(() => {
      savePlan();
    }, 1000);
  }

  function performUndo() {
    if (!site.value) return;
    const historyStore = useHistoryStore();
    const prev = historyStore.undo(site.value);
    if (prev) {
      site.value = prev;
      savePlan();
    }
  }

  function performRedo() {
    if (!site.value) return;
    const historyStore = useHistoryStore();
    const next = historyStore.redo(site.value);
    if (next) {
      site.value = next;
      savePlan();
    }
  }

  async function savePlan() {
    if (!currentPlanId.value || !site.value) return;
    isSaving.value = true;
    try {
      await api.updatePlan(currentPlanId.value, site.value);
      lastSavedAt.value = new Date();
    } catch (e: any) {
      error.value = e.message || "Auto-save failed";
    } finally {
      isSaving.value = false;
    }
  }

  function selectOverview() {
    currentBuildingId.value = null;
    currentFloorId.value = null;
  }

  function selectBuildingFloor(buildingId: string, floorId?: string) {
    currentBuildingId.value = buildingId;
    const b = site.value?.buildings.find((x) => x.id === buildingId);
    if (b && b.floors.length > 0) {
      currentFloorId.value = floorId || b.floors[0].id;
    }
  }

  function addEndpoint(endpoint: Endpoint) {
    if (!site.value) return;
    snapshotBeforeMutation();
    if (isOverview.value) {
      site.value.overview.endpoints.push(endpoint);
    } else {
      const f = currentFloor.value;
      if (f) {
        f.endpoints.push(endpoint);
      }
    }
    markDirtyAndAutosave();
  }

  function updateEndpoint(endpointId: string, updates: Partial<Endpoint>) {
    if (!site.value) return;
    const list = isOverview.value
      ? site.value.overview.endpoints
      : currentFloor.value?.endpoints;

    if (!list) return;
    const idx = list.findIndex((ep) => ep.id === endpointId);
    if (idx !== -1) {
      snapshotBeforeMutation();
      list[idx] = { ...list[idx], ...updates };
      markDirtyAndAutosave();
    }
  }

  function removeEndpoint(endpointId: string) {
    if (!site.value) return;
    snapshotBeforeMutation();
    if (isOverview.value) {
      site.value.overview.endpoints = site.value.overview.endpoints.filter((ep) => ep.id !== endpointId);
    } else {
      const f = currentFloor.value;
      if (f) {
        f.endpoints = f.endpoints.filter((ep) => ep.id !== endpointId);
      }
    }
    markDirtyAndAutosave();
  }

  function setBackground(asset: BackgroundAsset | null) {
    if (!site.value) return;
    snapshotBeforeMutation();
    if (isOverview.value) {
      site.value.overview.background = asset;
    } else {
      const f = currentFloor.value;
      if (f) {
        f.background = asset;
      }
    }
    markDirtyAndAutosave();
  }

  function setScale(scale: Scale | null) {
    if (!site.value) return;
    snapshotBeforeMutation();
    if (isOverview.value) {
      site.value.overview.scale = scale;
    } else {
      const f = currentFloor.value;
      if (f) {
        f.scale = scale;
      }
    }
    markDirtyAndAutosave();
  }

  function moveEndpoints(endpointIds: string[], dx: number, dy: number) {
    if (!site.value || endpointIds.length === 0) return;
    const list = isOverview.value ? site.value.overview.endpoints : currentFloor.value?.endpoints;
    if (!list) return;

    snapshotBeforeMutation();
    for (const ep of list) {
      if (endpointIds.includes(ep.id)) {
        ep.x += dx;
        ep.y += dy;
      }
    }
    markDirtyAndAutosave();
  }

  function groupEndpoints(endpointIds: string[], groupName = "Grouped Unit") {
    if (!site.value || endpointIds.length === 0) return;
    const list = isOverview.value ? site.value.overview.endpoints : currentFloor.value?.endpoints;
    if (!list) return;

    snapshotBeforeMutation();
    const newGroupId = "grp_" + Math.random().toString(36).substring(2, 8);
    for (const ep of list) {
      if (endpointIds.includes(ep.id)) {
        ep.group_id = newGroupId;
        ep.group_name = groupName;
      }
    }
    markDirtyAndAutosave();
  }

  function ungroupEndpoints(endpointIds: string[]) {
    if (!site.value || endpointIds.length === 0) return;
    const list = isOverview.value ? site.value.overview.endpoints : currentFloor.value?.endpoints;
    if (!list) return;

    snapshotBeforeMutation();
    for (const ep of list) {
      if (endpointIds.includes(ep.id)) {
        ep.group_id = null;
        ep.group_name = null;
      }
    }
    markDirtyAndAutosave();
  }

  function nestEndpoint(childId: string, parentId: string | null) {
    updateEndpoint(childId, { parent_id: parentId });
  }

  const currentSubAreas = computed<SubArea[]>(() => {
    return currentFloor.value?.sub_areas || [];
  });

  function addSubArea(subArea: SubArea) {
    if (!currentFloor.value) return;
    snapshotBeforeMutation();
    if (!currentFloor.value.sub_areas) {
      currentFloor.value.sub_areas = [];
    }
    currentFloor.value.sub_areas.push(subArea);
    markDirtyAndAutosave();
  }

  function removeSubArea(subAreaId: string) {
    if (!currentFloor.value || !currentFloor.value.sub_areas) return;
    snapshotBeforeMutation();
    currentFloor.value.sub_areas = currentFloor.value.sub_areas.filter((s) => s.id !== subAreaId);
    markDirtyAndAutosave();
  }

  const currentShapes = computed<Shape[]>(() => {
    if (isOverview.value) {
      return (site.value?.overview.shapes as Shape[]) || [];
    }
    return currentFloor.value?.shapes || [];
  });

  function addShape(shape: Shape) {
    if (!site.value) return;
    snapshotBeforeMutation();
    if (isOverview.value) {
      if (!site.value.overview.shapes) site.value.overview.shapes = [];
      site.value.overview.shapes.push(shape);
    } else if (currentFloor.value) {
      if (!currentFloor.value.shapes) currentFloor.value.shapes = [];
      currentFloor.value.shapes.push(shape);
    }
    markDirtyAndAutosave();
  }

  function updateShape(shapeId: string, updates: Partial<Shape>) {
    if (!site.value) return;
    const list = isOverview.value ? (site.value.overview.shapes as Shape[]) : currentFloor.value?.shapes;
    if (!list) return;

    const idx = list.findIndex((s) => s.id === shapeId);
    if (idx !== -1) {
      snapshotBeforeMutation();
      list[idx] = { ...list[idx], ...updates };
      markDirtyAndAutosave();
    }
  }

  function removeShape(shapeId: string) {
    if (!site.value) return;
    snapshotBeforeMutation();
    if (isOverview.value) {
      if (site.value.overview.shapes) {
        site.value.overview.shapes = (site.value.overview.shapes as Shape[]).filter((s) => s.id !== shapeId);
      }
    } else if (currentFloor.value?.shapes) {
      currentFloor.value.shapes = currentFloor.value.shapes.filter((s) => s.id !== shapeId);
    }
    markDirtyAndAutosave();
  }

  function addWallOpening(wallId: string, opening: WallOpening) {
    if (!site.value) return;
    const list = isOverview.value ? (site.value.overview.shapes as Shape[]) : currentFloor.value?.shapes;
    if (!list) return;

    const wall = list.find((s) => s.id === wallId && s.type === "wall");
    if (wall) {
      snapshotBeforeMutation();
      const geom = wall.geometry as WallGeometry;
      if (!geom.openings) geom.openings = [];
      geom.openings.push(opening);
      markDirtyAndAutosave();
    }
  }

  function removeWallOpening(wallId: string, openingId: string) {
    if (!site.value) return;
    const list = isOverview.value ? (site.value.overview.shapes as Shape[]) : currentFloor.value?.shapes;
    if (!list) return;

    const wall = list.find((s) => s.id === wallId && s.type === "wall");
    if (wall) {
      snapshotBeforeMutation();
      const geom = wall.geometry as WallGeometry;
      if (geom.openings) {
        geom.openings = geom.openings.filter((op) => op.id !== openingId);
        markDirtyAndAutosave();
      }
    }
  }

  return {
    currentPlanId,
    site,
    currentBuildingId,
    currentFloorId,
    isOverview,
    currentBuilding,
    currentFloor,
    currentEndpoints,
    currentSubAreas,
    currentShapes,
    isLoading,
    isSaving,
    lastSavedAt,
    error,
    loadPlan,
    savePlan,
    selectOverview,
    selectBuildingFloor,
    addEndpoint,
    updateEndpoint,
    removeEndpoint,
    moveEndpoints,
    groupEndpoints,
    ungroupEndpoints,
    nestEndpoint,
    addSubArea,
    removeSubArea,
    addShape,
    updateShape,
    removeShape,
    addWallOpening,
    removeWallOpening,
    performUndo,
    performRedo,
    setBackground,
    setScale,
  };
});
