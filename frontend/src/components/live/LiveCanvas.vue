<script setup lang="ts">
import { ref } from "vue";
import { useEditorStore } from "@/stores/editorStore";
import { usePlanStore } from "@/stores/planStore";
import { useSvgPanZoom } from "@/composables/useSvgPanZoom";
import type { Endpoint } from "@/types/plan";

import SvgDefs from "@/components/shared/SvgDefs.vue";
import BackgroundLayer from "@/components/editor/BackgroundLayer.vue";
import LiveEndpoint from "@/components/live/LiveEndpoint.vue";
import CameraSnapshotModal from "@/components/live/CameraSnapshotModal.vue";

const editorStore = useEditorStore();
const planStore = usePlanStore();

const svgRef = ref<SVGSVGElement | null>(null);
const { onMouseDown, onMouseMove, onMouseUp, onWheel } = useSvgPanZoom(svgRef);

const selectedCameraEndpoint = ref<Endpoint | null>(null);

function handleCameraClick(ep: Endpoint) {
  selectedCameraEndpoint.value = ep;
}

function closeCameraModal() {
  selectedCameraEndpoint.value = null;
}

// Directional arrow navigation for TV remotes and keyboard users
function handleDirectionalNav(e: KeyboardEvent, currentEp: Endpoint) {
  const arrowKeys = ["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"];
  if (!arrowKeys.includes(e.key)) return;

  const endpoints = planStore.currentEndpoints;
  if (endpoints.length <= 1) return;

  let bestNext: Endpoint | null = null;
  let minDistance = Infinity;

  for (const candidate of endpoints) {
    if (candidate.id === currentEp.id) continue;
    const dx = candidate.x - currentEp.x;
    const dy = candidate.y - currentEp.y;

    let isDirectionValid = false;
    if (e.key === "ArrowUp" && dy < -5) isDirectionValid = true;
    else if (e.key === "ArrowDown" && dy > 5) isDirectionValid = true;
    else if (e.key === "ArrowLeft" && dx < -5) isDirectionValid = true;
    else if (e.key === "ArrowRight" && dx > 5) isDirectionValid = true;

    if (isDirectionValid) {
      const dist = Math.hypot(dx, dy);
      if (dist < minDistance) {
        minDistance = dist;
        bestNext = candidate;
      }
    }
  }

  if (bestNext) {
    e.preventDefault();
    const el = document.getElementById(`endpoint-${bestNext.id}`);
    el?.focus();
  }
}
</script>

<template>
  <div
    class="canvas-container live-container"
    @wheel="onWheel"
    @mousedown="onMouseDown"
    @mousemove="onMouseMove"
    @mouseup="onMouseUp"
  >
    <svg ref="svgRef" class="live-svg">
      <SvgDefs />

      <!-- Canvas background grid (subtle in live mode) -->
      <rect width="100%" height="100%" fill="url(#canvas-grid)" />

      <!-- Transform container for Pan & Zoom -->
      <g :transform="`translate(${editorStore.panX}, ${editorStore.panY}) scale(${editorStore.zoom})`">
        <!-- Background floor plan -->
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
              fill="rgba(99, 102, 241, 0.04)"
              stroke="rgba(99, 102, 241, 0.25)"
              stroke-width="1.5"
              stroke-dasharray="4 4"
            />
            <text :x="sa.x + 8" :y="sa.y + 16" class="sub-area-label">{{ sa.name }}</text>
          </g>
        </g>

        <!-- Live state endpoints -->
        <g class="live-endpoints-layer">
          <LiveEndpoint
            v-for="ep in planStore.currentEndpoints"
            :id="`endpoint-${ep.id}`"
            :key="ep.id"
            :endpoint="ep"
            @click-camera="handleCameraClick"
            @keydown="handleDirectionalNav($event, ep)"
          />
        </g>
      </g>
    </svg>

    <!-- Windowed camera snapshot viewer -->
    <CameraSnapshotModal
      v-if="selectedCameraEndpoint"
      :endpoint="selectedCameraEndpoint"
      @close="closeCameraModal"
    />
  </div>
</template>

<style scoped>
.live-container {
  width: 100%;
  height: 100%;
  position: relative;
  overflow: hidden;
  user-select: none;
  background-color: var(--bg-primary);
  cursor: grab;
}

.live-container:active {
  cursor: grabbing;
}

.live-svg {
  width: 100%;
  height: 100%;
  display: block;
}

.sub-area-label {
  fill: #818cf8;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  pointer-events: none;
  opacity: 0.8;
}
</style>
