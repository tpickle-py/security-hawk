<script setup lang="ts">
import { ref, computed } from "vue";
import { useEditorStore } from "@/stores/editorStore";
import { usePlanStore } from "@/stores/planStore";
import { useSvgPanZoom } from "@/composables/useSvgPanZoom";
import type { Endpoint } from "@/types/plan";

import SvgDefs from "@/components/shared/SvgDefs.vue";
import BackgroundLayer from "@/components/editor/BackgroundLayer.vue";
import EndpointIcon from "@/components/editor/EndpointIcon.vue";
import ScaleTool from "@/components/editor/ScaleTool.vue";

const editorStore = useEditorStore();
const planStore = usePlanStore();

const svgRef = ref<SVGSVGElement | null>(null);
const { screenToSvg, onMouseDown: panZoomMouseDown, onMouseMove: panZoomMouseMove, onMouseUp: panZoomMouseUp, onWheel } = useSvgPanZoom(svgRef);

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

  if (isBoxSelecting.value && boxStart.value) {
    boxCurrent.value = screenToSvg(e.clientX, e.clientY);
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
  if (editorStore.isSettingScale) {
    const pt = screenToSvg(e.clientX, e.clientY);
    editorStore.addScalePoint(pt);
  }
}

function handleEndpointSelect(ep: Endpoint, e: MouseEvent) {
  editorStore.selectEndpoint(ep.id, e.shiftKey);
}

function handleEndpointDragStart(ep: Endpoint, e: MouseEvent) {
  if (editorStore.activeTool !== "select") return;

  // If endpoint is not selected, make it selected (respecting shiftKey)
  if (!editorStore.isEndpointSelected(ep.id)) {
    editorStore.selectEndpoint(ep.id, e.shiftKey);
  }

  isDraggingEndpoints.value = true;
  dragStartSvg.value = screenToSvg(e.clientX, e.clientY);

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
    const dx = currentSvg.x - dragStartSvg.value.x;
    const dy = currentSvg.y - dragStartSvg.value.y;

    // Move all selected endpoints together
    for (const [id, initialPos] of initialEndpointPositions.value.entries()) {
      planStore.updateEndpoint(id, {
        x: initialPos.x + dx,
        y: initialPos.y + dy,
      });
    }
  };

  const onDocMouseUp = () => {
    isDraggingEndpoints.value = false;
    initialEndpointPositions.value.clear();
    window.removeEventListener("mousemove", onDocMouseMove);
    window.removeEventListener("mouseup", onDocMouseUp);
  };

  window.addEventListener("mousemove", onDocMouseMove);
  window.addEventListener("mouseup", onDocMouseUp);
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
      coverage: null,
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
    >
      <SvgDefs />

      <!-- Background Canvas Grid -->
      <rect width="100%" height="100%" fill="url(#canvas-grid)" />

      <!-- Transform container for Pan & Zoom -->
      <g :transform="`translate(${editorStore.panX}, ${editorStore.panY}) scale(${editorStore.zoom})`">
        <!-- Background plan image -->
        <BackgroundLayer :background="planStore.currentFloor?.background || null" />

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
      </g>
    </svg>
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
</style>
