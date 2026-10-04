import { defineStore } from "pinia";
import { ref, computed } from "vue";
import type { Site, Floor, Endpoint, Scale, BackgroundAsset, SubArea, Shape, WallOpening, WallGeometry, RoomGeometry } from "@/types/plan";
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

  function moveEndpoints(endpointIds: string[], dx: number, dy: number, recordHistory = true) {
    if (!site.value || endpointIds.length === 0) return;
    const list = isOverview.value ? site.value.overview.endpoints : currentFloor.value?.endpoints;
    if (!list) return;

    if (recordHistory) {
      snapshotBeforeMutation();
    }
    for (const ep of list) {
      if (endpointIds.includes(ep.id)) {
        ep.x += dx;
        ep.y += dy;
      }
    }
    if (recordHistory) {
      markDirtyAndAutosave();
    }
  }

  function batchUpdateEndpoints(
    updates: Array<{ id: string } & Partial<Endpoint>>,
    recordHistory = true
  ) {
    if (!site.value || updates.length === 0) return;
    const list = isOverview.value ? site.value.overview.endpoints : currentFloor.value?.endpoints;
    if (!list) return;

    if (recordHistory) {
      snapshotBeforeMutation();
    }
    const updateMap = new Map(updates.map((u) => [u.id, u]));
    for (let i = 0; i < list.length; i++) {
      const u = updateMap.get(list[i].id);
      if (u) {
        const { id, ...changes } = u;
        Object.assign(list[i], changes);
      }
    }
    if (recordHistory) {
      markDirtyAndAutosave();
    }
  }

  function recenterEndpoints(targetEndpointIds?: string[]) {
    if (!site.value) return;
    const list = isOverview.value ? site.value.overview.endpoints : currentFloor.value?.endpoints;
    if (!list || list.length === 0) return;

    const toCenter = targetEndpointIds && targetEndpointIds.length > 0
      ? list.filter((ep) => targetEndpointIds.includes(ep.id))
      : list;

    if (toCenter.length === 0) return;

    // 1. Calculate bounding box of endpoints to center
    let minX = Infinity;
    let maxX = -Infinity;
    let minY = Infinity;
    let maxY = -Infinity;
    for (const ep of toCenter) {
      if (ep.x < minX) minX = ep.x;
      if (ep.x > maxX) maxX = ep.x;
      if (ep.y < minY) minY = ep.y;
      if (ep.y > maxY) maxY = ep.y;
    }
    const currentCenterX = (minX + maxX) / 2;
    const currentCenterY = (minY + maxY) / 2;

    // 2. Determine target center from background or shapes or fallback 600,450
    let targetX = 600;
    let targetY = 450;
    const bg = currentFloor.value?.background;
    if (bg && bg.width > 0 && bg.height > 0) {
      targetX = bg.x + bg.width / 2;
      targetY = bg.y + bg.height / 2;
    } else if (currentShapes.value.length > 0) {
      let sMinX = Infinity;
      let sMaxX = -Infinity;
      let sMinY = Infinity;
      let sMaxY = -Infinity;
      for (const s of currentShapes.value) {
        if (s.type === "wall" && s.geometry) {
          sMinX = Math.min(sMinX, (s.geometry as any).x1, (s.geometry as any).x2);
          sMaxX = Math.max(sMaxX, (s.geometry as any).x1, (s.geometry as any).x2);
          sMinY = Math.min(sMinY, (s.geometry as any).y1, (s.geometry as any).y2);
          sMaxY = Math.max(sMaxY, (s.geometry as any).y1, (s.geometry as any).y2);
        } else if (s.type === "room" && (s.geometry as any)?.points) {
          for (const [px, py] of (s.geometry as any).points) {
            sMinX = Math.min(sMinX, px);
            sMaxX = Math.max(sMaxX, px);
            sMinY = Math.min(sMinY, py);
            sMaxY = Math.max(sMaxY, py);
          }
        }
      }
      if (sMinX !== Infinity) {
        targetX = (sMinX + sMaxX) / 2;
        targetY = (sMinY + sMaxY) / 2;
      }
    }

    const dx = Math.round(targetX - currentCenterX);
    const dy = Math.round(targetY - currentCenterY);
    if (dx === 0 && dy === 0) return;

    snapshotBeforeMutation();
    for (const ep of toCenter) {
      ep.x += dx;
      ep.y += dy;
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

  function addRoomsGrid(opts: {
    cols: number;
    rows: number;
    startX: number;
    startY: number;
    roomWidth: number;
    roomHeight: number;
    names: string[];
    asSubAreas: boolean;
    parentAreaId?: string | null;
    createWalls?: boolean;
    createDoors?: boolean;
    wallThickness?: number;
  }) {
    if (!site.value || !currentFloor.value) return;
    snapshotBeforeMutation();

    const {
      cols,
      rows,
      startX,
      startY,
      roomWidth,
      roomHeight,
      names,
      asSubAreas,
      parentAreaId,
      createWalls = true,
      createDoors = true,
      wallThickness = 8,
    } = opts;

    const now = Date.now();

    if (asSubAreas) {
      if (!currentFloor.value.sub_areas) {
        currentFloor.value.sub_areas = [];
      }
      for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
          const idx = r * cols + c;
          const x = startX + c * roomWidth;
          const y = startY + r * roomHeight;
          const name = names[idx] || `Sub-Area ${idx + 1}`;
          currentFloor.value.sub_areas.push({
            id: `subarea_${now}_${r}_${c}_${Math.random().toString(36).substring(2, 7)}`,
            name,
            parent_area_id: parentAreaId || null,
            x,
            y,
            width: roomWidth,
            height: roomHeight,
            color: "rgba(59, 130, 246, 0.15)",
          });
        }
      }
    } else {
      const targetShapes: Shape[] = isOverview.value
        ? ((site.value.overview.shapes as Shape[]) || (site.value.overview.shapes = []))
        : ((currentFloor.value.shapes as Shape[]) || (currentFloor.value.shapes = []));

      // 1. Generate room polygons
      for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
          const idx = r * cols + c;
          const rx = startX + c * roomWidth;
          const ry = startY + r * roomHeight;
          const roomName = names[idx] || `Room ${idx + 1}`;

          targetShapes.push({
            id: `shape_${now}_room_${r}_${c}_${Math.random().toString(36).substring(2, 7)}`,
            type: "room",
            geometry: {
              points: [
                [rx, ry],
                [rx + roomWidth, ry],
                [rx + roomWidth, ry + roomHeight],
                [rx, ry + roomHeight],
              ],
              name: roomName,
            } as RoomGeometry,
            style: {
              fill: "rgba(99, 102, 241, 0.08)",
              stroke: "rgba(99, 102, 241, 0.4)",
              strokeWidth: 1,
            },
          });
        }
      }

      // 2. Generate architectural walls if requested
      if (createWalls) {
        // Horizontal wall segments (row boundaries: 0 to rows)
        for (let r = 0; r <= rows; r++) {
          const wy = startY + r * roomHeight;
          for (let c = 0; c < cols; c++) {
            const wx1 = startX + c * roomWidth;
            const wx2 = startX + (c + 1) * roomWidth;
            const openings: WallOpening[] = [];

            // Add door opening on interior dividing walls
            if (createDoors && r > 0 && r < rows) {
              const doorWidth = Math.min(80, Math.round(roomWidth * 0.4));
              openings.push({
                id: `opening_${now}_h_${r}_${c}`,
                type: "door",
                offset: Math.round((roomWidth - doorWidth) / 2),
                width: doorWidth,
                swingDirection: "right",
                openPercent: 90,
              });
            }

            targetShapes.push({
              id: `shape_${now}_wall_h_${r}_${c}_${Math.random().toString(36).substring(2, 7)}`,
              type: "wall",
              geometry: {
                x1: wx1,
                y1: wy,
                x2: wx2,
                y2: wy,
                thickness: wallThickness,
                openings,
              } as WallGeometry,
              style: {
                stroke: "#475569",
                strokeWidth: wallThickness,
              },
            });
          }
        }

        // Vertical wall segments (col boundaries: 0 to cols)
        for (let c = 0; c <= cols; c++) {
          const wx = startX + c * roomWidth;
          for (let r = 0; r < rows; r++) {
            const wy1 = startY + r * roomHeight;
            const wy2 = startY + (r + 1) * roomHeight;
            const openings: WallOpening[] = [];

            // Add door opening on interior vertical dividing walls if single row
            if (createDoors && c > 0 && c < cols && rows === 1) {
              const doorWidth = Math.min(80, Math.round(roomHeight * 0.4));
              openings.push({
                id: `opening_${now}_v_${c}_${r}`,
                type: "door",
                offset: Math.round((roomHeight - doorWidth) / 2),
                width: doorWidth,
                swingDirection: "right",
                openPercent: 90,
              });
            }

            targetShapes.push({
              id: `shape_${now}_wall_v_${c}_${r}_${Math.random().toString(36).substring(2, 7)}`,
              type: "wall",
              geometry: {
                x1: wx,
                y1: wy1,
                x2: wx,
                y2: wy2,
                thickness: wallThickness,
                openings,
              } as WallGeometry,
              style: {
                stroke: "#475569",
                strokeWidth: wallThickness,
              },
            });
          }
        }
      }
    }

    markDirtyAndAutosave();
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
    batchUpdateEndpoints,
    recenterEndpoints,
    snapshotBeforeMutation,
    markDirtyAndAutosave,
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
    addRoomsGrid,
    performUndo,
    performRedo,
    setBackground,
    setScale,
  };
});
