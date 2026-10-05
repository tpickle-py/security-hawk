<script setup lang="ts">
import { ref, computed, nextTick } from "vue";
import { useEditorStore, VIEWPORT_CONFIGS } from "@/stores/editorStore";
import { usePlanStore } from "@/stores/planStore";
import { useEntityStore } from "@/stores/entityStore";
import { useSvgPanZoom } from "@/composables/useSvgPanZoom";
import type { Endpoint, Shape, SubArea, RoomGeometry, WallGeometry } from "@/types/plan";

import SvgDefs from "@/components/shared/SvgDefs.vue";
import BackgroundLayer from "@/components/editor/BackgroundLayer.vue";
import EndpointIcon from "@/components/editor/EndpointIcon.vue";
import ScaleTool from "@/components/editor/ScaleTool.vue";
import ShapesLayer from "@/components/editor/ShapesLayer.vue";
import EditorContextMenu, { type ContextMenuState } from "@/components/editor/EditorContextMenu.vue";
import { useSnapEngine, type SnapResult, type AlignmentGuide } from "@/composables/useSnapEngine";

const editorStore = useEditorStore();
const planStore = usePlanStore();
const entityStore = useEntityStore();
const { extractVertices, snapCoordinate, findSmartAlignment } = useSnapEngine();

function isOrphaned(ep: Endpoint) {
  if (ep.type === "composite") return false;
  return !entityStore.isKnownEntity(ep.entity_id);
}

const svgRef = ref<SVGSVGElement | null>(null);
const { screenToSvg, onMouseDown: panZoomMouseDown, onMouseMove: panZoomMouseMove, onMouseUp: panZoomMouseUp, onWheel } = useSvgPanZoom(svgRef);

// Cursor tracking & Magnetic snap state
const cursorPoint = ref<{ x: number; y: number } | null>(null);
const currentSnapResult = ref<SnapResult | null>(null);
const activeGuides = ref<AlignmentGuide[]>([]);

// Inline Room & SubArea Renaming
interface InlineRenameState {
  targetId: string | null;
  targetType: "subarea" | "room" | null;
  name: string;
  x: number;
  y: number;
}
const inlineRenameState = ref<InlineRenameState>({
  targetId: null,
  targetType: null,
  name: "",
  x: 0,
  y: 0,
});
const inlineRenameInputRef = ref<HTMLInputElement | null>(null);

function startInlineRename(type: "subarea" | "room", target: any) {
  const currentName = type === "subarea" ? target.name : target.geometry?.name || "Room";
  let x = target.x || 100;
  let y = target.y || 100;
  if (type === "room" && target.geometry?.points?.length > 0) {
    const pts = target.geometry.points;
    let sumX = 0, sumY = 0;
    for (const p of pts) { sumX += p[0]; sumY += p[1]; }
    x = Math.round(sumX / pts.length) - 75;
    y = Math.round(sumY / pts.length) - 15;
  }
  inlineRenameState.value = {
    targetId: target.id,
    targetType: type,
    name: currentName,
    x,
    y,
  };
  nextTick(() => {
    inlineRenameInputRef.value?.focus();
    inlineRenameInputRef.value?.select();
  });
}

function commitInlineRename() {
  if (!inlineRenameState.value.targetId) return;
  const newName = inlineRenameState.value.name.trim();
  if (newName) {
    if (inlineRenameState.value.targetType === "subarea") {
      planStore.updateSubArea(inlineRenameState.value.targetId, { name: newName });
    } else if (inlineRenameState.value.targetType === "room") {
      const sh = planStore.currentFloor?.shapes.find((s) => s.id === inlineRenameState.value.targetId);
      if (sh) {
        planStore.updateShape(sh.id, { geometry: { ...(sh.geometry || {}), name: newName } });
      }
    }
  }
  inlineRenameState.value.targetId = null;
}

function cancelInlineRename() {
  inlineRenameState.value.targetId = null;
}

// Marquee / Box Selection
const isBoxSelecting = ref(false);
const boxStart = ref<{ x: number; y: number } | null>(null);
const boxCurrent = ref<{ x: number; y: number } | null>(null);

const marqueeRect = computed(() => {
  if (!boxStart.value || !boxCurrent.value) return null;
  const x = Math.min(boxStart.value.x, boxCurrent.value.x);
  const y = Math.min(boxStart.value.y, boxCurrent.value.y);
  const width = Math.abs(boxCurrent.value.x - boxStart.value.x);
  const height = Math.abs(boxCurrent.value.y - boxStart.value.y);
  return { x, y, width, height };
});

// Dragging placed endpoint(s) on canvas
const isDraggingEndpoints = ref(false);
const dragStartSvg = ref<{ x: number; y: number }>({ x: 0, y: 0 });
const initialEndpointPositions = ref<Map<string, { x: number; y: number }>>(new Map());

function handleCanvasMouseDown(e: MouseEvent) {
  // If pan tool or middle mouse or spacebar, delegate to pan/zoom
  if (editorStore.activeTool === "pan" || e.button === 1 || e.altKey) {
    panZoomMouseDown(e);
    return;
  }

  // If clicking canvas background with select tool, start box selection
  if (e.button === 0 && editorStore.activeTool === "select" && !editorStore.isSettingScale) {
    const pt = screenToSvg(e.clientX, e.clientY);
    isBoxSelecting.value = true;
    boxStart.value = pt;
    boxCurrent.value = pt;

    if (!e.shiftKey) {
      editorStore.clearSelection();
    }
  }
}

function handleCanvasMouseMove(e: MouseEvent) {
  panZoomMouseMove(e);

  const raw = screenToSvg(e.clientX, e.clientY);

  // Calculate magnetic snap coordinates
  const vertices = extractVertices(planStore.currentShapes, planStore.currentEndpoints);
  const origin = editorStore.drawingPoints[0] || null;
  const snapRes = snapCoordinate(raw.x, raw.y, vertices, {
    originPoint: origin,
    shiftKey: e.shiftKey,
    gridEnabled: true,
  });
  currentSnapResult.value = snapRes;
  cursorPoint.value = { x: snapRes.x, y: snapRes.y };

  if (isBoxSelecting.value && boxStart.value) {
    boxCurrent.value = raw;
  }
}

function handleCanvasMouseUp(e: MouseEvent) {
  panZoomMouseUp();

  if (isBoxSelecting.value && marqueeRect.value) {
    const rect = marqueeRect.value;
    if (rect.width > 5 || rect.height > 5) {
      // Find all endpoints inside marquee box
      const selectedIds: string[] = [];
      for (const ep of planStore.currentEndpoints) {
        if (
          ep.x >= rect.x &&
          ep.x <= rect.x + rect.width &&
          ep.y >= rect.y &&
          ep.y <= rect.y + rect.height
        ) {
          selectedIds.push(ep.id);
        }
      }
      if (e.shiftKey) {
        // Merge with existing
        const combined = new Set([...editorStore.selectedEndpointIds, ...selectedIds]);
        editorStore.selectAll(Array.from(combined));
      } else {
        editorStore.selectAll(selectedIds);
      }
    }
    isBoxSelecting.value = false;
    boxStart.value = null;
    boxCurrent.value = null;
  }
}

function handleCanvasClick(e: MouseEvent) {
  const pt = cursorPoint.value || screenToSvg(e.clientX, e.clientY);

  if (editorStore.isSettingScale) {
    editorStore.addScalePoint(pt);
    return;
  }

  // Wall Drawing Tool
  if (editorStore.activeTool === "wall") {
    if (editorStore.drawingPoints.length === 0) {
      editorStore.drawingPoints.push(pt);
    } else {
      const p0 = editorStore.drawingPoints[0];
      if (Math.hypot(pt.x - p0.x, pt.y - p0.y) >= 10) {
        planStore.addShape({
          id: "wall_" + Math.random().toString(36).substring(2, 9),
          type: "wall",
          geometry: {
            x1: p0.x,
            y1: p0.y,
            x2: pt.x,
            y2: pt.y,
            thickness: editorStore.activeWallThickness,
            openings: [],
          },
          style: {
            stroke: editorStore.activeWallColor,
          },
        });
        if (e.shiftKey) {
          // Chain connected walls
          editorStore.drawingPoints = [pt];
        } else {
          editorStore.drawingPoints = [];
        }
      }
    }
    return;
  }

  // Room Polygon Tool
  if (editorStore.activeTool === "room") {
    if (editorStore.drawingPoints.length >= 3) {
      const p0 = editorStore.drawingPoints[0];
      if (Math.hypot(pt.x - p0.x, pt.y - p0.y) < 20) {
        closeRoomPolygon();
        return;
      }
    }
    editorStore.drawingPoints.push(pt);
    return;
  }

  // Architectural Label Tool
  if (editorStore.activeTool === "label") {
    const text = prompt("Enter label text:", "Room / Area");
    if (text && text.trim()) {
      planStore.addShape({
        id: "lbl_" + Math.random().toString(36).substring(2, 9),
        type: "label",
        geometry: {
          x: pt.x,
          y: pt.y,
          text: text.trim(),
          fontSize: 13,
        },
        style: {
          color: "#cbd5e1",
        },
      });
    }
    return;
  }
}

function handleCanvasDoubleClick() {
  if (editorStore.activeTool === "room" && editorStore.drawingPoints.length >= 3) {
    closeRoomPolygon();
  }
}

function closeRoomPolygon() {
  const name = prompt("Enter room name:", "Living Room") || "Room";
  planStore.addShape({
    id: "rm_" + Math.random().toString(36).substring(2, 9),
    type: "room",
    geometry: {
      points: [...editorStore.drawingPoints.map((p) => [p.x, p.y] as [number, number])],
      name,
    },
    style: {
      fill: editorStore.activeRoomFill,
      stroke: editorStore.activeRoomStroke,
    },
  });
  editorStore.drawingPoints = [];
}

function handleWallClick(wallId: string, clickPoint: { x: number; y: number }) {
  const wall = planStore.currentShapes.find((s) => s.id === wallId && s.type === "wall");
  if (!wall) return;

  const geom = wall.geometry as WallGeometry;
  const dx = geom.x2 - geom.x1;
  const dy = geom.y2 - geom.y1;
  const len = Math.hypot(dx, dy);
  if (len < 30) return;

  const ux = dx / len;
  const uy = dy / len;
  // Project click onto wall vector
  const proj = (clickPoint.x - geom.x1) * ux + (clickPoint.y - geom.y1) * uy;
  const offset = Math.max(10, Math.min(len - 45, Math.round(proj - 18)));

  const opType = editorStore.activeTool === "window" ? "window" : "door";
  planStore.addWallOpening(wallId, {
    id: "op_" + Math.random().toString(36).substring(2, 9),
    type: opType,
    offset,
    width: 36,
  });
}

let dragMovementOccurred = false;
let pendingSelectionEndpoint: string | null = null;

function handleEndpointSelect(ep: Endpoint, e: MouseEvent) {
  // If user clicked an endpoint that is already in multi-selection without Shift,
  // do not immediately collapse the selection—wait until mouseup so they can drag all selected items!
  if (editorStore.selectedEndpointIds.length > 1 && editorStore.isEndpointSelected(ep.id) && !e.shiftKey) {
    pendingSelectionEndpoint = ep.id;
    return;
  }
  pendingSelectionEndpoint = null;
  editorStore.selectEndpoint(ep.id, e.shiftKey);
}

function handleEndpointDragStart(ep: Endpoint, e: MouseEvent) {
  if (editorStore.activeTool !== "select") return;

  // If endpoint is not selected, make it selected
  if (!editorStore.isEndpointSelected(ep.id)) {
    editorStore.selectEndpoint(ep.id, e.shiftKey);
    pendingSelectionEndpoint = null;
  }

  isDraggingEndpoints.value = true;
  dragMovementOccurred = false;
  dragStartSvg.value = screenToSvg(e.clientX, e.clientY);

  // Take undo snapshot ONCE at start of drag
  planStore.snapshotBeforeMutation();

  // Record initial positions of all selected endpoints
  const posMap = new Map<string, { x: number; y: number }>();
  for (const item of planStore.currentEndpoints) {
    if (editorStore.isEndpointSelected(item.id)) {
      posMap.set(item.id, { x: item.x, y: item.y });
    }
  }
  initialEndpointPositions.value = posMap;

  const onDocMouseMove = (moveEvent: MouseEvent) => {
    if (!isDraggingEndpoints.value) return;
    const currentSvg = screenToSvg(moveEvent.clientX, moveEvent.clientY);
    const dx = Math.round(currentSvg.x - dragStartSvg.value.x);
    const dy = Math.round(currentSvg.y - dragStartSvg.value.y);

    if (Math.hypot(dx, dy) >= 2) {
      dragMovementOccurred = true;
    }

    // Move all selected endpoints smoothly in real time without snapshotting history on every frame
    const updates = Array.from(initialEndpointPositions.value.entries()).map(([id, initialPos]) => ({
      id,
      x: initialPos.x + dx,
      y: initialPos.y + dy,
    }));
    planStore.batchUpdateEndpoints(updates, false);
  };

  const onDocMouseUp = () => {
    isDraggingEndpoints.value = false;
    initialEndpointPositions.value.clear();
    window.removeEventListener("mousemove", onDocMouseMove);
    window.removeEventListener("mouseup", onDocMouseUp);

    if (dragMovementOccurred) {
      planStore.markDirtyAndAutosave();
    } else if (pendingSelectionEndpoint) {
      // User simply clicked one of the multiple selected items without dragging
      editorStore.selectEndpoint(pendingSelectionEndpoint, false);
    }
    pendingSelectionEndpoint = null;
  };

  window.addEventListener("mousemove", onDocMouseMove);
  window.addEventListener("mouseup", onDocMouseUp);
}

// Room & Sub-Area Selection & Dragging
function handleSubAreaDragStart(sa: SubArea, e: MouseEvent) {
  if (editorStore.activeTool !== "select" || e.button !== 0) return;
  editorStore.selectSubArea(sa.id);

  const startSvg = screenToSvg(e.clientX, e.clientY);
  const origX = sa.x;
  const origY = sa.y;
  planStore.snapshotBeforeMutation();

  const onDocMouseMove = (moveEvent: MouseEvent) => {
    const cur = screenToSvg(moveEvent.clientX, moveEvent.clientY);
    let targetX = origX + Math.round(cur.x - startSvg.x);
    let targetY = origY + Math.round(cur.y - startSvg.y);

    // Magnetic alignment check against other subareas
    const otherBoxes = planStore.currentSubAreas
      .filter((other) => other.id !== sa.id)
      .map((other) => ({ x: other.x, y: other.y, width: other.width, height: other.height }));
    const alignResult = findSmartAlignment({ x: targetX, y: targetY, width: sa.width, height: sa.height }, otherBoxes, 8);
    targetX = alignResult.snappedX;
    targetY = alignResult.snappedY;
    activeGuides.value = alignResult.guides;

    planStore.updateSubArea(sa.id, { x: targetX, y: targetY }, false);
  };

  const onDocMouseUp = () => {
    activeGuides.value = [];
    window.removeEventListener("mousemove", onDocMouseMove);
    window.removeEventListener("mouseup", onDocMouseUp);
    planStore.markDirtyAndAutosave();
  };

  window.addEventListener("mousemove", onDocMouseMove);
  window.addEventListener("mouseup", onDocMouseUp);
}

function handleRoomShapeDragStart(shape: Shape, e: MouseEvent) {
  if (editorStore.activeTool !== "select" || e.button !== 0) return;
  editorStore.selectShape(shape.id);

  const geom = shape.geometry as RoomGeometry;
  if (!geom.points || geom.points.length === 0) return;

  const startSvg = screenToSvg(e.clientX, e.clientY);
  const origPoints = geom.points.map((p) => [p[0], p[1]] as [number, number]);
  planStore.snapshotBeforeMutation();

  const onDocMouseMove = (moveEvent: MouseEvent) => {
    const cur = screenToSvg(moveEvent.clientX, moveEvent.clientY);
    const dx = Math.round(cur.x - startSvg.x);
    const dy = Math.round(cur.y - startSvg.y);
    const newPoints = origPoints.map(([px, py]) => [px + dx, py + dy] as [number, number]);
    planStore.resizeRoomShape(shape.id, newPoints, false);
  };

  const onDocMouseUp = () => {
    window.removeEventListener("mousemove", onDocMouseMove);
    window.removeEventListener("mouseup", onDocMouseUp);
    planStore.markDirtyAndAutosave();
  };

  window.addEventListener("mousemove", onDocMouseMove);
  window.addEventListener("mouseup", onDocMouseUp);
}

// Room & Sub-Area Bounding Box & 8 Resize Handles
interface RoomBounds {
  x: number;
  y: number;
  width: number;
  height: number;
  id: string;
  type: "subarea" | "room";
  name: string;
}

const selectedRoomBounds = computed<RoomBounds | null>(() => {
  if (editorStore.selectedSubAreaId) {
    const sa = planStore.currentSubAreas.find((s) => s.id === editorStore.selectedSubAreaId);
    if (sa) {
      return {
        x: sa.x,
        y: sa.y,
        width: sa.width,
        height: sa.height,
        id: sa.id,
        type: "subarea",
        name: sa.name,
      };
    }
  }

  if (editorStore.selectedShapeId) {
    const shape = planStore.currentShapes.find((s) => s.id === editorStore.selectedShapeId);
    if (shape && shape.type === "room") {
      const geom = shape.geometry as RoomGeometry;
      if (geom.points && geom.points.length > 0) {
        let minX = Infinity;
        let minY = Infinity;
        let maxX = -Infinity;
        let maxY = -Infinity;
        for (const [px, py] of geom.points) {
          if (px < minX) minX = px;
          if (px > maxX) maxX = px;
          if (py < minY) minY = py;
          if (py > maxY) maxY = py;
        }
        return {
          x: minX,
          y: minY,
          width: Math.max(10, maxX - minX),
          height: Math.max(10, maxY - minY),
          id: shape.id,
          type: "room",
          name: geom.name || "Room",
        };
      }
    }
  }

  return null;
});

function getResizeHandles(bounds: RoomBounds) {
  const { x, y, width: w, height: h } = bounds;
  return [
    { type: "nw", x, y, cursor: "nwse-resize" },
    { type: "n", x: x + w / 2, y, cursor: "ns-resize" },
    { type: "ne", x: x + w, y, cursor: "nesw-resize" },
    { type: "e", x: x + w, y: y + h / 2, cursor: "ew-resize" },
    { type: "se", x: x + w, y: y + h, cursor: "nwse-resize" },
    { type: "s", x: x + w / 2, y: y + h, cursor: "ns-resize" },
    { type: "sw", x, y: y + h, cursor: "nesw-resize" },
    { type: "w", x, y: y + h / 2, cursor: "ew-resize" },
  ];
}

function handleResizeHandleDown(handleType: string, e: MouseEvent) {
  const bounds = selectedRoomBounds.value;
  if (!bounds || e.button !== 0) return;

  const startSvg = screenToSvg(e.clientX, e.clientY);
  const origX = bounds.x;
  const origY = bounds.y;
  const origW = bounds.width;
  const origH = bounds.height;
  planStore.snapshotBeforeMutation();

  let initialPoints: Array<[number, number]> = [];
  if (bounds.type === "room") {
    const shape = planStore.currentShapes.find((s) => s.id === bounds.id);
    if (shape && shape.type === "room") {
      initialPoints = (shape.geometry as RoomGeometry).points.map((p) => [p[0], p[1]]);
    }
  }

  const onDocMouseMove = (moveEvent: MouseEvent) => {
    const cur = screenToSvg(moveEvent.clientX, moveEvent.clientY);
    const dx = Math.round(cur.x - startSvg.x);
    const dy = Math.round(cur.y - startSvg.y);

    let newX = origX;
    let newY = origY;
    let newW = origW;
    let newH = origH;

    if (handleType.includes("w")) {
      const targetW = origW - dx;
      if (targetW >= 20) {
        newX = origX + dx;
        newW = targetW;
      } else {
        newX = origX + origW - 20;
        newW = 20;
      }
    } else if (handleType.includes("e")) {
      newW = Math.max(20, origW + dx);
    }

    if (handleType.includes("n")) {
      const targetH = origH - dy;
      if (targetH >= 20) {
        newY = origY + dy;
        newH = targetH;
      } else {
        newY = origY + origH - 20;
        newH = 20;
      }
    } else if (handleType.includes("s")) {
      newH = Math.max(20, origH + dy);
    }

    if (bounds.type === "subarea") {
      planStore.updateSubArea(bounds.id, { x: newX, y: newY, width: newW, height: newH }, false);
    } else if (bounds.type === "room" && initialPoints.length > 0) {
      const scaleX = newW / origW;
      const scaleY = newH / origH;
      const newPoints = initialPoints.map(([px, py]) => [
        Math.round(newX + (px - origX) * scaleX),
        Math.round(newY + (py - origY) * scaleY),
      ] as [number, number]);
      planStore.resizeRoomShape(bounds.id, newPoints, false);
    }
  };

  const onDocMouseUp = () => {
    window.removeEventListener("mousemove", onDocMouseMove);
    window.removeEventListener("mouseup", onDocMouseUp);
    planStore.markDirtyAndAutosave();
  };

  window.addEventListener("mousemove", onDocMouseMove);
  window.addEventListener("mouseup", onDocMouseUp);
}

// Right-Click Context Menu
const contextMenuState = ref<ContextMenuState>({
  show: false,
  x: 0,
  y: 0,
  type: "canvas",
  target: null,
});

function openContextMenu(e: MouseEvent, type: any, target: any) {
  e.preventDefault();
  contextMenuState.value = {
    show: true,
    x: e.clientX,
    y: e.clientY,
    type,
    target,
  };
}

function handleContextMenuAction(actionName: string) {
  const target = contextMenuState.value.target as any;
  switch (actionName) {
    case "rotate-cw":
      if (target && "rotation" in target) {
        planStore.updateEndpoint(target.id, { rotation: ((target.rotation || 0) + 90) % 360 });
      }
      break;
    case "rotate-ccw":
      if (target && "rotation" in target) {
        planStore.updateEndpoint(target.id, { rotation: ((target.rotation || 0) - 90 + 360) % 360 });
      }
      break;
    case "invert-180":
      if (target && "rotation" in target) {
        planStore.updateEndpoint(target.id, { rotation: ((target.rotation || 0) + 180) % 360 });
      }
      break;
    case "duplicate":
      if (target && "entity_id" in target) {
        const dup: Endpoint = {
          ...target,
          id: "ep_" + Math.random().toString(36).substring(2, 9),
          x: target.x + 25,
          y: target.y + 25,
        };
        planStore.addEndpoint(dup);
        editorStore.selectEndpoint(dup.id);
      }
      break;
    case "delete":
      if (target) {
        if ("entity_id" in target) {
          planStore.removeEndpoint(target.id);
          editorStore.clearSelection();
        } else if ("type" in target && target.type) {
          planStore.removeShape(target.id);
          editorStore.clearSelection();
        } else if ("width" in target && "height" in target) {
          planStore.removeSubArea(target.id);
          editorStore.clearSelection();
        }
      }
      break;
    case "rename-room":
      if (target) {
        const currentName = target.name || (target.geometry as any)?.name || "Room";
        const newName = prompt("Rename room:", currentName);
        if (newName && newName.trim()) {
          if ("width" in target) {
            planStore.updateSubArea(target.id, { name: newName.trim() });
          } else {
            const geom = { ...(target.geometry || {}), name: newName.trim() };
            planStore.updateShape(target.id, { geometry: geom });
          }
        }
      }
      break;
    case "add-door":
      if (target && target.type === "wall") {
        editorStore.setTool("door");
      }
      break;
    case "add-window":
      if (target && target.type === "wall") {
        editorStore.setTool("window");
      }
      break;
    case "insert-room-grid":
      editorStore.showRoomGridModal = true;
      break;
    case "tool-wall":
      editorStore.setTool("wall");
      break;
    case "tool-room":
      editorStore.setTool("room");
      break;
    case "tool-label":
      editorStore.setTool("label");
      break;
    case "toggle-cad":
      editorStore.toggleCadCommandBar();
      break;
    case "calibrate-scale":
      editorStore.startScaleCalibration();
      break;
    case "zoom-fit":
      editorStore.resetView();
      break;
    case "save-plan":
      planStore.savePlan();
      break;
  }
}

// Viewport Simulator State
const activeViewportConfig = computed(() => {
  if (editorStore.activeViewport === "freeform") return null;
  return VIEWPORT_CONFIGS[editorStore.activeViewport] || null;
});

const viewportRect = computed(() => {
  const cfg = activeViewportConfig.value;
  if (!cfg || cfg.width <= 0) return null;

  // Find center of floor plan
  let centerX = 600;
  let centerY = 450;
  const bg = planStore.currentFloor?.background;
  if (bg && bg.width > 0 && bg.height > 0) {
    centerX = bg.x + bg.width / 2;
    centerY = bg.y + bg.height / 2;
  }

  const baseDim = bg && bg.width > 0 ? Math.max(bg.width, bg.height) : 900;
  const scale = Math.max(baseDim / Math.min(cfg.width, cfg.height), 0.8);
  const frameW = Math.round(cfg.width * scale);
  const frameH = Math.round(cfg.height * scale);

  return {
    x: Math.round(centerX - frameW / 2),
    y: Math.round(centerY - frameH / 2),
    width: frameW,
    height: frameH,
    rawWidth: cfg.width,
    rawHeight: cfg.height,
    label: cfg.label,
    aspect: cfg.aspectRatio,
  };
});

function fitViewToActiveViewport() {
  if (!svgRef.value || !viewportRect.value) return;
  const rect = svgRef.value.getBoundingClientRect();
  const vr = viewportRect.value;
  editorStore.fitToView(rect.width, rect.height, {
    minX: vr.x,
    maxX: vr.x + vr.width,
    minY: vr.y,
    maxY: vr.y + vr.height,
  });
}

// Drag & drop from EntityPicker
function onDragOver(e: DragEvent) {
  e.preventDefault();
  if (e.dataTransfer) {
    e.dataTransfer.dropEffect = "copy";
  }
}

function isPointInPoly(pt: { x: number; y: number }, points: [number, number][]): boolean {
  let inside = false;
  for (let i = 0, j = points.length - 1; i < points.length; j = i++) {
    const xi = points[i][0];
    const yi = points[i][1];
    const xj = points[j][0];
    const yj = points[j][1];
    const intersect = yi > pt.y !== yj > pt.y && pt.x < ((xj - xi) * (pt.y - yi)) / (yj - yi) + xi;
    if (intersect) inside = !inside;
  }
  return inside;
}

function findRoomAtPoint(x: number, y: number): { name: string; areaId?: string | null } | null {
  for (const sub of planStore.currentFloor?.sub_areas || []) {
    if (x >= sub.x && x <= sub.x + sub.width && y >= sub.y && y <= sub.y + sub.height) {
      return { name: sub.name, areaId: sub.parent_area_id };
    }
  }
  for (const shape of planStore.currentFloor?.shapes || []) {
    if (shape.type === "room" && (shape.geometry as any)?.points) {
      if (isPointInPoly({ x, y }, (shape.geometry as any).points)) {
        return { name: (shape.geometry as any).name || "Room" };
      }
    }
  }
  return null;
}

function onDrop(e: DragEvent) {
  e.preventDefault();
  if (!e.dataTransfer) return;

  const dataStr = e.dataTransfer.getData("application/json");
  if (!dataStr) return;

  try {
    const data = JSON.parse(dataStr);
    const dropCoord = screenToSvg(e.clientX, e.clientY);

    const newEndpoint: Endpoint = {
      id: "ep_" + Math.random().toString(36).substring(2, 9),
      entity_id: data.entity_id,
      device_id: data.device_id || null,
      type: data.type || "generic",
      x: dropCoord.x,
      y: dropCoord.y,
      rotation: 0,
      label: data.label || data.entity_id,
      companions: [],
      cameras: [],
      coverage:
        data.type === "camera"
          ? { type: "cone", range: 120, angle: 70 }
          : data.type === "motion"
          ? { type: "cone", range: 85, angle: 85 }
          : null,
      stale_after: null,
    };

    planStore.addEndpoint(newEndpoint);
    editorStore.selectEndpoint(newEndpoint.id);

    // Auto-designate room if dropped inside a room or subarea
    if (data.entity_id) {
      const hitRoom = findRoomAtPoint(dropCoord.x, dropCoord.y);
      if (hitRoom) {
        let matchedAreaId = hitRoom.areaId;
        if (!matchedAreaId) {
          const area = entityStore.areas.find(
            (a) =>
              a.name.toLowerCase() === hitRoom.name.toLowerCase() ||
              (a.aliases && a.aliases.some((al) => al.toLowerCase() === hitRoom.name.toLowerCase()))
          );
          if (area) {
            matchedAreaId = area.area_id;
          }
        }
        if (matchedAreaId) {
          entityStore.designateArea(data.entity_id, matchedAreaId);
        }
      }
    }
  } catch (err) {
    console.error("Failed to drop entity", err);
  }
}
</script>

<template>
  <div
    class="canvas-container"
    @dragover="onDragOver"
    @drop="onDrop"
    @wheel="onWheel"
    @mousedown="handleCanvasMouseDown"
    @mousemove="handleCanvasMouseMove"
    @mouseup="handleCanvasMouseUp"
  >
    <svg
      ref="svgRef"
      class="editor-svg"
      @click="handleCanvasClick"
      @dblclick="handleCanvasDoubleClick"
      @contextmenu.prevent="openContextMenu($event, 'canvas', null)"
    >
      <SvgDefs />

      <!-- Background Canvas Grid -->
      <rect width="100%" height="100%" fill="url(#canvas-grid)" />

      <!-- Transform container for Pan & Zoom -->
      <g :transform="`translate(${editorStore.panX}, ${editorStore.panY}) scale(${editorStore.zoom})`">
        <!-- Background plan image -->
        <BackgroundLayer :background="planStore.currentFloor?.background || null" />

        <!-- Architectural Vector Shapes Layer (Rooms, Walls, Openings, Labels, Snapping) -->
        <ShapesLayer
          :shapes="planStore.currentShapes"
          :active-snap-point="currentSnapResult"
          :cursor-point="cursorPoint"
          @select-shape="editorStore.selectShape"
          @wall-click="handleWallClick"
          @room-drag-start="handleRoomShapeDragStart"
          @room-dblclick="(shape) => startInlineRename('room', shape)"
          @shape-contextmenu="(shape, ev) => openContextMenu(ev, shape.type, shape)"
        />

        <!-- Sub-Areas / Rooms Layer -->
        <g class="sub-areas-layer" v-if="planStore.currentSubAreas.length > 0">
          <g
            v-for="sa in planStore.currentSubAreas"
            :key="sa.id"
            class="sub-area-item"
            :class="{ selected: editorStore.selectedSubAreaId === sa.id }"
            @mousedown.stop="handleSubAreaDragStart(sa, $event)"
            @dblclick.stop="startInlineRename('subarea', sa)"
            @contextmenu.prevent.stop="openContextMenu($event, 'subarea', sa)"
          >
            <rect
              :x="sa.x"
              :y="sa.y"
              :width="sa.width"
              :height="sa.height"
              rx="6"
              :fill="sa.color || 'rgba(99, 102, 241, 0.08)'"
              :stroke="editorStore.selectedSubAreaId === sa.id ? '#818cf8' : 'rgba(99, 102, 241, 0.4)'"
              :stroke-width="editorStore.selectedSubAreaId === sa.id ? 2.5 : 1.5"
              :stroke-dasharray="editorStore.selectedSubAreaId === sa.id ? 'none' : '4 4'"
            />
            <text :x="sa.x + 8" :y="sa.y + 18" class="sub-area-label">{{ sa.name }}</text>
          </g>
        </g>

        <!-- Selected Room / SubArea Bounding Box & 8 Resize Handles -->
        <g v-if="selectedRoomBounds" class="room-resize-overlay">
          <!-- Bounding dashed outline with corner glow -->
          <rect
            :x="selectedRoomBounds.x - 2"
            :y="selectedRoomBounds.y - 2"
            :width="selectedRoomBounds.width + 4"
            :height="selectedRoomBounds.height + 4"
            fill="none"
            stroke="#6366f1"
            stroke-width="1.5"
            stroke-dasharray="4 3"
            pointer-events="none"
          />
          <!-- Dimension pill on top -->
          <g :transform="`translate(${selectedRoomBounds.x + selectedRoomBounds.width / 2}, ${selectedRoomBounds.y - 12})`" pointer-events="none">
            <rect x="-44" y="-14" width="88" height="18" rx="4" fill="rgba(15, 23, 42, 0.9)" stroke="#6366f1" stroke-width="1" />
            <text text-anchor="middle" y="0" font-size="10" font-weight="600" fill="#e2e8f0" font-family="monospace">
              {{ Math.round(selectedRoomBounds.width) }} × {{ Math.round(selectedRoomBounds.height) }}
            </text>
          </g>
          <!-- 8 Resize Handles: NW, N, NE, E, SE, S, SW, W -->
          <rect
            v-for="handle in getResizeHandles(selectedRoomBounds)"
            :key="handle.type"
            :x="handle.x - 5"
            :y="handle.y - 5"
            width="10"
            height="10"
            rx="2"
            fill="#ffffff"
            stroke="#6366f1"
            stroke-width="2"
            :style="{ cursor: handle.cursor }"
            @mousedown.stop="handleResizeHandleDown(handle.type, $event)"
          />
        </g>

        <!-- Scale Calibration Layer -->
        <ScaleTool />

        <!-- Placed Endpoints -->
        <g class="endpoints-layer">
          <EndpointIcon
            v-for="ep in planStore.currentEndpoints"
            :key="ep.id"
            :endpoint="ep"
            :is-selected="editorStore.isEndpointSelected(ep.id)"
            :is-orphaned="isOrphaned(ep)"
            @select="handleEndpointSelect"
            @drag-start="handleEndpointDragStart"
            @contextmenu.prevent.stop="openContextMenu($event, 'endpoint', ep)"
          />
        </g>

        <!-- Marquee Selection Rectangle -->
        <rect
          v-if="marqueeRect && (marqueeRect.width > 2 || marqueeRect.height > 2)"
          :x="marqueeRect.x"
          :y="marqueeRect.y"
          :width="marqueeRect.width"
          :height="marqueeRect.height"
          fill="rgba(99, 102, 241, 0.15)"
          stroke="#6366f1"
          stroke-width="1.5"
          stroke-dasharray="4 2"
        />

        <!-- Magnetic Smart Alignment Guides -->
        <g v-if="activeGuides.length > 0" class="alignment-guides-layer" pointer-events="none">
          <line
            v-for="(guide, gIdx) in activeGuides"
            :key="gIdx"
            :x1="guide.x1"
            :y1="guide.y1"
            :x2="guide.x2"
            :y2="guide.y2"
            stroke="#06b6d4"
            stroke-width="1.5"
            stroke-dasharray="4 3"
          />
        </g>

        <!-- Inline Room / SubArea Renaming Overlay -->
        <foreignObject
          v-if="inlineRenameState.targetId"
          :x="inlineRenameState.x"
          :y="inlineRenameState.y"
          width="180"
          height="34"
          class="inline-rename-foreign"
        >
          <div xmlns="http://www.w3.org/1999/xhtml" class="inline-rename-wrapper">
            <input
              ref="inlineRenameInputRef"
              v-model="inlineRenameState.name"
              class="inline-rename-input"
              @keydown.enter.prevent="commitInlineRename"
              @keydown.esc.prevent="cancelInlineRename"
              @blur="commitInlineRename"
            />
          </div>
        </foreignObject>

        <!-- Viewport Simulator Frame (Phone / Tablet / TV / Ultrawide) -->
        <g v-if="viewportRect && editorStore.showViewportGuides" class="viewport-guide-layer">
          <!-- Darkened backdrop with cut-out mask -->
          <mask id="viewport-mask">
            <rect x="-10000" y="-10000" width="30000" height="30000" fill="white" />
            <rect
              :x="viewportRect.x"
              :y="viewportRect.y"
              :width="viewportRect.width"
              :height="viewportRect.height"
              rx="8"
              fill="black"
            />
          </mask>
          <!-- Shaded overlay outside viewport safe zone -->
          <rect
            x="-10000"
            y="-10000"
            width="30000"
            height="30000"
            fill="rgba(0, 0, 0, 0.45)"
            mask="url(#viewport-mask)"
            pointer-events="none"
          />

          <!-- Viewport boundary frame -->
          <rect
            :x="viewportRect.x"
            :y="viewportRect.y"
            :width="viewportRect.width"
            :height="viewportRect.height"
            rx="8"
            fill="none"
            stroke="#6366f1"
            stroke-width="2.5"
            stroke-dasharray="8 4"
            class="viewport-border-rect"
            pointer-events="none"
          />

          <!-- Device Aspect Label Tag at top-left of frame -->
          <g :transform="`translate(${viewportRect.x}, ${viewportRect.y - 28})`" pointer-events="none">
            <rect
              x="0"
              y="0"
              :width="Math.max(viewportRect.label.length * 8 + 60, 170)"
              height="24"
              rx="4"
              fill="rgba(30, 41, 59, 0.94)"
              stroke="#6366f1"
              stroke-width="1.2"
            />
            <text
              x="8"
              y="16"
              fill="#ffffff"
              font-size="11"
              font-weight="bold"
            >
              {{ activeViewportConfig?.icon }} {{ viewportRect.label }} ({{ viewportRect.aspect }})
            </text>
          </g>

          <!-- Device Dimension Tag at bottom-right of frame -->
          <g :transform="`translate(${viewportRect.x + viewportRect.width}, ${viewportRect.y + viewportRect.height + 6})`" pointer-events="none">
            <text
              x="0"
              y="14"
              text-anchor="end"
              fill="#94a3b8"
              font-size="11"
              font-family="monospace"
              font-weight="600"
            >
              Target: {{ viewportRect.rawWidth }} × {{ viewportRect.rawHeight }}px
            </text>
          </g>
        </g>
      </g>
    </svg>

    <!-- Viewport Floating Banner -->
    <div v-if="viewportRect" class="viewport-preview-pill glass-panel">
      <span class="vp-pill-icon">{{ activeViewportConfig?.icon }}</span>
      <span class="vp-pill-text">Simulating Viewport: <strong>{{ activeViewportConfig?.label }}</strong></span>
      <button class="vp-pill-btn" @click="fitViewToActiveViewport" title="Auto-zoom to fit this simulated viewport">
        ⛶ Fit View
      </button>
      <button class="vp-pill-btn close" @click="editorStore.setViewport('freeform')" title="Exit Viewport Simulation">
        ✕ Exit
      </button>
    </div>

    <!-- Right-Click Context Menu Modal Popup -->
    <EditorContextMenu
      :menu-state="contextMenuState"
      @close="contextMenuState.show = false"
      @action="handleContextMenuAction"
    />
  </div>
</template>

<style scoped>
.canvas-container {
  width: 100%;
  height: 100%;
  position: relative;
  overflow: hidden;
  user-select: none;
  background-color: var(--bg-primary);
}

.editor-svg {
  width: 100%;
  height: 100%;
  display: block;
  cursor: default;
}

.sub-area-label {
  fill: #a5b4fc;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  pointer-events: none;
}

.viewport-border-rect {
  filter: drop-shadow(0 0 6px rgba(99, 102, 241, 0.4));
}

/* Floating Viewport Preview Banner */
.viewport-preview-pill {
  position: absolute;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 16px;
  border-radius: var(--radius-full, 9999px);
  background: rgba(15, 23, 42, 0.88);
  border: 1px solid rgba(99, 102, 241, 0.5);
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.5);
  z-index: 150;
  animation: fadeIn 0.2s ease;
}

.vp-pill-icon {
  font-size: 14px;
}

.vp-pill-text {
  font-size: 12px;
  color: var(--text-primary);
}

.vp-pill-text strong {
  color: #a5b4fc;
}

.vp-pill-btn {
  background: rgba(99, 102, 241, 0.2);
  border: 1px solid rgba(99, 102, 241, 0.4);
  color: #ffffff;
  font-size: 11px;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: var(--radius-sm, 6px);
  cursor: pointer;
  transition: all 0.15s ease;
}

.vp-pill-btn:hover {
  background: rgba(99, 102, 241, 0.4);
}

.vp-pill-btn.close {
  background: rgba(239, 68, 68, 0.15);
  border-color: rgba(239, 68, 68, 0.35);
  color: #fca5a5;
}

.vp-pill-btn.close:hover {
  background: rgba(239, 68, 68, 0.3);
  color: #ffffff;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translate(-50%, 8px);
  }
  to {
    opacity: 1;
    transform: translate(-50%, 0);
  }
}

.alignment-guides-layer line {
  pointer-events: none;
  filter: drop-shadow(0 0 3px rgba(6, 182, 212, 0.8));
}

.inline-rename-foreign {
  overflow: visible;
  pointer-events: auto;
}

.inline-rename-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
}

.inline-rename-input {
  width: 170px;
  background: rgba(15, 23, 42, 0.95);
  color: #ffffff;
  border: 1.5px solid #6366f1;
  border-radius: 4px;
  padding: 4px 8px;
  font-size: 13px;
  font-weight: 600;
  outline: none;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5), 0 0 8px rgba(99, 102, 241, 0.4);
  text-align: center;
}

.inline-rename-input:focus {
  border-color: #818cf8;
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.6), 0 0 12px rgba(129, 140, 248, 0.6);
}
</style>
