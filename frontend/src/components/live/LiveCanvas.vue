<script setup lang="ts">
import { ref, watch } from "vue";
import { useEditorStore } from "@/stores/editorStore";
import { usePlanStore } from "@/stores/planStore";
import { useLiveStore } from "@/stores/liveStore";
import { useSvgPanZoom } from "@/composables/useSvgPanZoom";
import type { Endpoint } from "@/types/plan";

import SvgDefs from "@/components/shared/SvgDefs.vue";
import BackgroundLayer from "@/components/editor/BackgroundLayer.vue";
import ShapesLayer from "@/components/editor/ShapesLayer.vue";
import LiveEndpoint from "@/components/live/LiveEndpoint.vue";
import CameraSnapshotModal from "@/components/live/CameraSnapshotModal.vue";
import EventFeedDrawer from "@/components/live/EventFeedDrawer.vue";

const editorStore = useEditorStore();
const planStore = usePlanStore();
const liveStore = useLiveStore();

const svgRef = ref<SVGSVGElement | null>(null);
const { onMouseDown, onMouseMove, onMouseUp, onWheel } = useSvgPanZoom(svgRef);

const selectedCameraEndpoint = ref<Endpoint | null>(null);
const popupTriggeredBy = ref<string>("");
const popupAutoDismissSeconds = ref<number>(0);

function handleCameraClick(ep: Endpoint) {
  selectedCameraEndpoint.value = ep;
  popupTriggeredBy.value = "";
  popupAutoDismissSeconds.value = 0;
}

function closeCameraModal() {
  selectedCameraEndpoint.value = null;
  popupTriggeredBy.value = "";
  popupAutoDismissSeconds.value = 0;
}

// Watch for state changes to trigger Linked Camera Auto-Popup & Follow Activity
watch(
  () => liveStore.lastEventTime,
  () => {
    for (const ep of planStore.currentEndpoints) {
      const st = liveStore.getState(ep.entity_id)?.state?.toLowerCase();
      const isActive = st === "on" || st === "detected" || st === "open";

      if (isActive) {
        // 1. Linked Camera Auto-Popup (30s countdown)
        if (ep.cameras && ep.cameras.length > 0 && !selectedCameraEndpoint.value) {
          const camEntityId = ep.cameras[0];
          let camEp = planStore.currentEndpoints.find((x) => x.entity_id === camEntityId);
          if (!camEp) {
            camEp = {
              id: "ep_auto_cam",
              entity_id: camEntityId,
              type: "camera",
              label: `Camera (${ep.label || ep.entity_id})`,
              x: 0,
              y: 0,
              rotation: 0,
              device_id: null,
              companions: [],
              cameras: [],
              coverage: null,
              stale_after: null,
            };
          }
          selectedCameraEndpoint.value = camEp;
          popupTriggeredBy.value = ep.label || ep.entity_id;
          popupAutoDismissSeconds.value = 30;
        }

        // 2. Follow-Activity Mode (pans to active sensor, quiet-return after 120s)
        if (liveStore.followActivityEnabled) {
          editorStore.panX = -ep.x * editorStore.zoom + window.innerWidth / 2;
          editorStore.panY = -ep.y * editorStore.zoom + window.innerHeight / 2;
          liveStore.highlightEndpoint(ep.id);

          liveStore.resetQuietReturn(() => {
            planStore.selectOverview();
            editorStore.resetView();
          });
        }
      }
    }
  }
);

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
    <!-- Live Floating Control Bar -->
    <div class="live-floating-bar glass-panel">
      <button
        class="live-control-btn"
        :class="{ active: liveStore.followActivityEnabled }"
        title="Follow Activity Mode: auto-focus to active sensors with 120s quiet return"
        @click="liveStore.toggleFollowActivity"
      >
        <span class="live-status-dot" :class="{ pulsing: liveStore.followActivityEnabled }"></span>
        <span>Follow Activity</span>
      </button>

      <button class="live-control-btn" title="Reset View Zoom" @click="editorStore.resetView">
        <svg viewBox="0 0 24 24" width="14" height="14">
          <path fill="currentColor" d="M12 4V1L8 5l4 4V6c3.31 0 6 2.69 6 6 0 1.01-.25 1.97-.7 2.8l1.46 1.46A7.93 7.93 0 0 0 20 12c0-4.42-3.58-8-8-8zm0 14c-3.31 0-6-2.69-6-6 0-1.01.25-1.97.7-2.8L5.24 7.74A7.93 7.93 0 0 0 4 12c0 4.42 3.58 8 8 8v3l4-4-4-4v3z"/>
        </svg>
        <span>Reset</span>
      </button>
    </div>

    <svg ref="svgRef" class="live-svg">
      <SvgDefs />

      <!-- Canvas background grid (subtle in live mode) -->
      <rect width="100%" height="100%" fill="url(#canvas-grid)" />

      <!-- Transform container for Pan & Zoom -->
      <g :transform="`translate(${editorStore.panX}, ${editorStore.panY}) scale(${editorStore.zoom})`">
        <!-- Background floor plan -->
        <BackgroundLayer :background="planStore.currentFloor?.background || null" />

        <!-- Vector Architectural Shapes (Rooms, Walls, Cutouts, Labels) -->
        <ShapesLayer :shapes="planStore.currentShapes" />

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

    <!-- Live Event Feed Drawer -->
    <EventFeedDrawer />

    <!-- Windowed camera snapshot viewer -->
    <CameraSnapshotModal
      v-if="selectedCameraEndpoint"
      :endpoint="selectedCameraEndpoint"
      :auto-dismiss-seconds="popupAutoDismissSeconds"
      :triggered-by="popupTriggeredBy"
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

.live-floating-bar {
  position: absolute;
  top: 16px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  z-index: 100;
  border-radius: var(--radius-full, 9999px);
}

.live-control-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 12px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-full, 9999px);
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 500;
  transition: all 0.2s ease;
}

.live-control-btn:hover {
  background: var(--bg-surface-hover);
  color: var(--text-primary);
}

.live-control-btn.active {
  background: rgba(99, 102, 241, 0.2);
  border-color: #6366f1;
  color: #a5b4fc;
}

.live-status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--text-muted);
}

.live-control-btn.active .live-status-dot {
  background: #6366f1;
  box-shadow: 0 0 8px #6366f1;
}

.live-status-dot.pulsing {
  animation: liveDotPulse 1.2s infinite;
}

@keyframes liveDotPulse {
  0% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.4); opacity: 0.5; }
  100% { transform: scale(1); opacity: 1; }
}
</style>
