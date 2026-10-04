<script setup lang="ts">
import { ref, computed } from "vue";
import { useEditorStore, VIEWPORT_CONFIGS } from "@/stores/editorStore";
import { usePlanStore } from "@/stores/planStore";
import { useEntityStore } from "@/stores/entityStore";
import { useSvgPanZoom } from "@/composables/useSvgPanZoom";
import type { Endpoint } from "@/types/plan";

import SvgDefs from "@/components/shared/SvgDefs.vue";
import BackgroundLayer from "@/components/editor/BackgroundLayer.vue";
import EndpointIcon from "@/components/editor/EndpointIcon.vue";
import ScaleTool from "@/components/editor/ScaleTool.vue";
import ShapesLayer from "@/components/editor/ShapesLayer.vue";
import { useSnapEngine, type SnapResult } from "@/composables/useSnapEngine";
import type { WallGeometry } from "@/types/plan";

const editorStore = useEditorStore();
const planStore = usePlanStore();
const entityStore = useEntityStore();
const { extractVertices, snapCoordinate } = useSnapEngine();

function isOrphaned(ep: Endpoint) {
  if (ep.type === "composite") return false;
  return !entityStore.isKnownEntity(ep.entity_id);
}

const svgRef = ref<SVGSVGElement | null>(null);
const { screenToSvg, onMouseDown: panZoomMouseDown, onMouseMove: panZoomMouseMove, onMouseUp: panZoomMouseUp, onWheel } = useSvgPanZoom(svgRef);

// Cursor tracking & Magnetic snap state
const cursorPoint = ref<{ x: number; y: number } | null>(null);
const currentSnapResult = ref<SnapResult | null>(null);

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
        />

        <!-- Sub-Areas / Rooms Layer -->
        <g class="sub-areas-layer" v-if="planStore.currentSubAreas.length > 0">
          <g v-for="sa in planStore.currentSubAreas" :key="sa.id">
            <rect
              :x="sa.x"
              :y="sa.y"
              :width="sa.width"
              :height="sa.height"
              rx="6"
              fill="rgba(99, 102, 241, 0.08)"
              stroke="rgba(99, 102, 241, 0.4)"
              stroke-width="1.5"
              stroke-dasharray="4 4"
            />
            <text :x="sa.x + 8" :y="sa.y + 16" class="sub-area-label">{{ sa.name }}</text>
          </g>
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
</style>
