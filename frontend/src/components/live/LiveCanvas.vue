<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from "vue";
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
const { onWheel } = useSvgPanZoom(svgRef);

// Fixed Position & TV/Phone HUD state
const isPositionLocked = ref(localStorage.getItem("sh_live_locked") === "true");
const showNavControls = ref(true);
const isFullscreen = ref(Boolean(document.fullscreenElement));

// Live Drag & Touch state
const isLiveDragging = ref(false);
const liveDragStart = ref({ x: 0, y: 0 });
const livePanStart = ref({ x: 0, y: 0 });

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

// Watch for state changes to trigger Linked Camera Auto-Popup, Follow Activity & Motion Trails
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

        // 3. Spatio-Temporal Motion Traversal Trail
        if (ep.type === "motion" || ep.type === "door") {
          liveStore.recordTraversalNode(ep, planStore.currentFloorId);
        }
      }
    }
  }
);

// Motion Traversal Trail Computed
const activeTrail = computed(() => liveStore.activeTrail);
const trailPath = computed(() => {
  if (!liveStore.motionTrailsEnabled || !activeTrail.value) return "";
  const nodes = activeTrail.value.nodes;
  if (!nodes || nodes.length < 2) return "";
  return nodes.reduce((acc, pt, idx) => {
    return idx === 0 ? `M ${pt.x} ${pt.y}` : `${acc} L ${pt.x} ${pt.y}`;
  }, "");
});

// Site Overview: Building State Roll-Up (Spec §Views)
const buildingRollups = computed(() => {
  if (!planStore.site || !planStore.site.buildings) return [];
  return planStore.site.buildings.map((b) => {
    let doorsOpen = 0;
    let doorsTotal = 0;
    let motionActive = false;
    let activeMotionSensors: string[] = [];
    let totalEndpoints = 0;

    for (const f of b.floors) {
      for (const ep of f.endpoints) {
        totalEndpoints += 1;
        const st = liveStore.getState(ep.entity_id)?.state?.toLowerCase();
        const isActive = st === "on" || st === "detected" || st === "open";

        if (ep.type === "door" || ep.type === "window") {
          doorsTotal += 1;
          if (isActive) doorsOpen += 1;
        }

        if (ep.type === "motion" && isActive) {
          motionActive = true;
          activeMotionSensors.push(ep.label || ep.entity_id);
        }
      }
    }

    const isAlert = doorsOpen > 0 || motionActive;

    return {
      id: b.id,
      name: b.name,
      x: b.x || 150,
      y: b.y || 150,
      floorsCount: b.floors.length,
      primaryFloorId: b.floors[0]?.id || null,
      doorsOpen,
      doorsTotal,
      motionActive,
      activeMotionSensors,
      totalEndpoints,
      isAlert,
    };
  });
});

function jumpToBuilding(buildingId: string, floorId: string | null) {
  if (floorId) {
    planStore.selectBuildingFloor(buildingId, floorId);
  }
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

// Live Mouse Drag Panning
function onLiveMouseDown(e: MouseEvent) {
  if (isPositionLocked.value) return;
  if (e.button === 0 || e.button === 1) {
    isLiveDragging.value = true;
    liveDragStart.value = { x: e.clientX, y: e.clientY };
    livePanStart.value = { x: editorStore.panX, y: editorStore.panY };
  }
}

function onLiveMouseMove(e: MouseEvent) {
  if (isPositionLocked.value || !isLiveDragging.value) return;
  const dx = e.clientX - liveDragStart.value.x;
  const dy = e.clientY - liveDragStart.value.y;
  editorStore.panX = livePanStart.value.x + dx;
  editorStore.panY = livePanStart.value.y + dy;
}

function onLiveMouseUp() {
  isLiveDragging.value = false;
}

function onLiveWheel(e: WheelEvent) {
  if (isPositionLocked.value) return;
  onWheel(e);
}

// Live Touch Pan & Pinch-Zoom (Phone / Tablet / Wall-Mount)
let initialPinchDistance = 0;
let initialPinchZoom = 1;

function onTouchStart(e: TouchEvent) {
  if (isPositionLocked.value) return;

  if (e.touches.length === 1) {
    isLiveDragging.value = true;
    const t = e.touches[0];
    liveDragStart.value = { x: t.clientX, y: t.clientY };
    livePanStart.value = { x: editorStore.panX, y: editorStore.panY };
  } else if (e.touches.length === 2) {
    isLiveDragging.value = false;
    const t1 = e.touches[0];
    const t2 = e.touches[1];
    initialPinchDistance = Math.hypot(t2.clientX - t1.clientX, t2.clientY - t1.clientY);
    initialPinchZoom = editorStore.zoom;
  }
}

function onTouchMove(e: TouchEvent) {
  if (isPositionLocked.value) return;

  if (e.touches.length === 1 && isLiveDragging.value) {
    const t = e.touches[0];
    const dx = t.clientX - liveDragStart.value.x;
    const dy = t.clientY - liveDragStart.value.y;
    editorStore.panX = livePanStart.value.x + dx;
    editorStore.panY = livePanStart.value.y + dy;
  } else if (e.touches.length === 2 && initialPinchDistance > 0) {
    const t1 = e.touches[0];
    const t2 = e.touches[1];
    const dist = Math.hypot(t2.clientX - t1.clientX, t2.clientY - t1.clientY);
    const factor = dist / initialPinchDistance;
    editorStore.zoom = Math.min(Math.max(initialPinchZoom * factor, 0.2), 6.0);
  }
}

function onTouchEnd() {
  isLiveDragging.value = false;
  initialPinchDistance = 0;
}

// Navigation Actions for TVs and Phones
function panCanvas(dx: number, dy: number) {
  editorStore.panX += dx;
  editorStore.panY += dy;
}

function zoomIn() {
  editorStore.zoomIn();
}

function zoomOut() {
  editorStore.zoomOut();
}

function fitToScreen() {
  let minX = Infinity;
  let maxX = -Infinity;
  let minY = Infinity;
  let maxY = -Infinity;

  const bg = planStore.currentFloor?.background;
  if (bg && bg.width > 0 && bg.height > 0) {
    minX = Math.min(minX, bg.x);
    maxX = Math.max(maxX, bg.x + bg.width);
    minY = Math.min(minY, bg.y);
    maxY = Math.max(maxY, bg.y + bg.height);
  }

  for (const ep of planStore.currentEndpoints) {
    minX = Math.min(minX, ep.x - 30);
    maxX = Math.max(maxX, ep.x + 30);
    minY = Math.min(minY, ep.y - 30);
    maxY = Math.max(maxY, ep.y + 30);
  }

  const containerW = window.innerWidth;
  const containerH = window.innerHeight;

  editorStore.fitToView(containerW, containerH, {
    minX: minX === Infinity ? 0 : minX,
    maxX: maxX === -Infinity ? 1200 : maxX,
    minY: minY === Infinity ? 0 : minY,
    maxY: maxY === -Infinity ? 800 : maxY,
  });
}

function togglePositionLock() {
  isPositionLocked.value = !isPositionLocked.value;
  localStorage.setItem("sh_live_locked", String(isPositionLocked.value));
}

function toggleFullscreen() {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen().catch(() => {});
  } else {
    document.exitFullscreen().catch(() => {});
  }
}

function onGlobalKeyDown(e: KeyboardEvent) {
  const tag = (e.target as HTMLElement)?.tagName?.toLowerCase();
  if (tag === "input" || tag === "textarea") return;

  if (e.key === "ArrowUp") {
    e.preventDefault();
    panCanvas(0, 100);
  } else if (e.key === "ArrowDown") {
    e.preventDefault();
    panCanvas(0, -100);
  } else if (e.key === "ArrowLeft") {
    e.preventDefault();
    panCanvas(100, 0);
  } else if (e.key === "ArrowRight") {
    e.preventDefault();
    panCanvas(-100, 0);
  } else if (e.key === "+" || e.key === "=") {
    zoomIn();
  } else if (e.key === "-" || e.key === "_") {
    zoomOut();
  } else if (e.key === "0" || e.key === "Home") {
    fitToScreen();
  } else if (e.key.toLowerCase() === "l") {
    togglePositionLock();
  } else if (e.key.toLowerCase() === "f") {
    toggleFullscreen();
  }
}

function updateFullscreenState() {
  isFullscreen.value = Boolean(document.fullscreenElement);
}

onMounted(() => {
  window.addEventListener("keydown", onGlobalKeyDown);
  document.addEventListener("fullscreenchange", updateFullscreenState);
});

onUnmounted(() => {
  window.removeEventListener("keydown", onGlobalKeyDown);
  document.removeEventListener("fullscreenchange", updateFullscreenState);
});
</script>

<template>
  <div
    class="canvas-container live-container"
    :class="{ 'position-locked': isPositionLocked }"
    @wheel="onLiveWheel"
    @mousedown="onLiveMouseDown"
    @mousemove="onLiveMouseMove"
    @mouseup="onLiveMouseUp"
    @touchstart="onTouchStart"
    @touchmove="onTouchMove"
    @touchend="onTouchEnd"
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

      <button
        class="live-control-btn"
        :class="{ active: liveStore.motionTrailsEnabled }"
        title="Toggle Motion Traversal Trails (shows occupant movement path)"
        @click="liveStore.toggleMotionTrails"
      >
        <span>〰️ Motion Trails</span>
      </button>

      <button
        v-if="liveStore.activeTrail && liveStore.motionTrailsEnabled"
        class="live-control-btn clear-trail-btn"
        title="Clear active motion trail"
        @click="liveStore.clearMotionTrails"
      >
        <span>Clear Trail</span>
      </button>

      <button
        class="live-control-btn lock-btn"
        :class="{ active: isPositionLocked }"
        :title="isPositionLocked ? 'Position is fixed/locked (tablet/TV mode)' : 'Position is free to pan & zoom'"
        @click="togglePositionLock"
      >
        <span v-if="isPositionLocked">🔒 Fixed Position</span>
        <span v-else>🔓 Free Pan</span>
      </button>

      <button class="live-control-btn" title="Fit floor plan to screen" @click="fitToScreen">
        <svg viewBox="0 0 24 24" width="14" height="14">
          <path fill="currentColor" d="M5 5h5V3H3v7h2V5zm14-2h-7v2h5v5h2V3zm0 14h-2v5h-5v2h7v-7zM5 14H3v7h7v-2H5v-5z"/>
        </svg>
        <span>Fit Screen</span>
      </button>

      <button class="live-control-btn" title="Reset View Zoom" @click="editorStore.resetView">
        <svg viewBox="0 0 24 24" width="14" height="14">
          <path fill="currentColor" d="M12 4V1L8 5l4 4V6c3.31 0 6 2.69 6 6 0 1.01-.25 1.97-.7 2.8l1.46 1.46A7.93 7.93 0 0 0 20 12c0-4.42-3.58-8-8-8zm0 14c-3.31 0-6-2.69-6-6 0-1.01.25-1.97.7-2.8L5.24 7.74A7.93 7.93 0 0 0 4 12c0 4.42 3.58 8 8 8v3l4-4-4-4v3z"/>
        </svg>
        <span>Reset</span>
      </button>
    </div>

    <!-- Site Overview: Building State Roll-Up Floating Overlay (Spec §Views) -->
    <div v-if="planStore.isOverview && buildingRollups.length > 0" class="overview-rollups-overlay glass-panel">
      <div class="rollups-header">
        <span class="rollups-title">🏢 Site Overview · Building Roll-Up</span>
        <span class="rollups-count">{{ buildingRollups.length }} Structure(s)</span>
      </div>
      <div class="rollups-grid">
        <div
          v-for="b in buildingRollups"
          :key="b.id"
          class="building-rollup-card"
          :class="{ 'has-alert': b.isAlert }"
          @click="jumpToBuilding(b.id, b.primaryFloorId)"
        >
          <div class="b-card-top">
            <span class="b-name">{{ b.name }}</span>
            <span class="b-status-pill" :class="b.isAlert ? 'pill-alert' : 'pill-secure'">
              {{ b.isAlert ? '⚠️ ALERT' : '🛡️ SECURE' }}
            </span>
          </div>

          <div class="b-metrics">
            <div class="b-metric-row">
              <span class="m-label">🚪 Doors & Windows:</span>
              <span class="m-val" :class="{ 'val-alert': b.doorsOpen > 0 }">
                {{ b.doorsOpen > 0 ? `${b.doorsOpen} OPEN` : 'All Closed' }}
              </span>
            </div>
            <div class="b-metric-row">
              <span class="m-label">🏃 Motion Activity:</span>
              <span class="m-val" :class="{ 'val-alert': b.motionActive }">
                {{ b.motionActive ? 'Motion Detected' : 'Quiet' }}
              </span>
            </div>
          </div>

          <div class="b-card-footer">
            <span class="floors-hint">{{ b.floorsCount }} floor(s) · {{ b.totalEndpoints }} endpoints</span>
            <span class="jump-arrow">Inspect Floor →</span>
          </div>
        </div>
      </div>
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

        <!-- Spatio-Temporal Motion Traversal Trail Layer -->
        <g class="motion-traversal-layer" v-if="liveStore.motionTrailsEnabled && activeTrail">
          <!-- Flowing Trail Path Line -->
          <path
            v-if="trailPath"
            :d="trailPath"
            fill="none"
            stroke="url(#motion-trail-gradient)"
            stroke-width="3.5"
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-dasharray="8 5"
            class="traversal-animated-line"
            filter="url(#glow-trail)"
          />

          <!-- Traversal Nodes (Breadcrumb checkpoints) -->
          <g
            v-for="(node, nIdx) in activeTrail.nodes"
            :key="node.id"
            :transform="`translate(${node.x}, ${node.y})`"
            class="traversal-node"
          >
            <!-- Node outer pulse if it's the latest occupant position -->
            <circle
              v-if="nIdx === activeTrail.nodes.length - 1"
              cx="0"
              cy="0"
              r="22"
              fill="rgba(245, 158, 11, 0.25)"
              stroke="#f59e0b"
              stroke-width="2"
              class="occupant-lead-pulse"
            />

            <!-- Checkpoint circle -->
            <circle cx="0" cy="0" r="10" fill="#1e1e2e" stroke="#f59e0b" stroke-width="2" />

            <!-- Sequence number #1, #2, #3 -->
            <text
              x="0"
              y="0"
              text-anchor="middle"
              dominant-baseline="central"
              fill="#ffffff"
              font-size="9"
              font-weight="bold"
            >
              {{ node.sequenceIndex }}
            </text>

            <!-- Elapsed time badge pill -->
            <g transform="translate(0, -16)">
              <rect x="-16" y="-7" width="32" height="13" rx="3" fill="rgba(15, 23, 42, 0.85)" stroke="#6366f1" stroke-width="0.8" />
              <text x="0" y="0" text-anchor="middle" dominant-baseline="central" fill="#a5b4fc" font-size="8" font-weight="600">
                +{{ node.elapsedSeconds }}s
              </text>
            </g>
          </g>
        </g>

        <!-- Site Overview Building Markers on Canvas -->
        <g class="overview-buildings-layer" v-if="planStore.isOverview">
          <g
            v-for="b in buildingRollups"
            :key="b.id"
            :transform="`translate(${b.x}, ${b.y})`"
            class="overview-building-marker"
            @click="jumpToBuilding(b.id, b.primaryFloorId)"
          >
            <rect
              x="-85"
              y="-45"
              width="170"
              height="90"
              rx="8"
              :fill="b.isAlert ? 'rgba(239, 68, 68, 0.18)' : 'rgba(30, 41, 59, 0.90)'"
              :stroke="b.isAlert ? '#ef4444' : '#6366f1'"
              stroke-width="2"
              class="building-box"
            />
            <text x="0" y="-20" text-anchor="middle" fill="#ffffff" font-size="13" font-weight="bold">{{ b.name }}</text>
            <text x="0" y="2" text-anchor="middle" :fill="b.isAlert ? '#f87171' : '#34d399'" font-size="10" font-weight="600">
              {{ b.isAlert ? (b.doorsOpen > 0 ? `${b.doorsOpen} Door(s) Open` : 'Motion Detected') : '🛡️ Secure' }}
            </text>
            <text x="0" y="24" text-anchor="middle" fill="#94a3b8" font-size="9">Click to Enter Floor →</text>
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

    <!-- TV & Phone Navigation Controls HUD -->
    <div class="live-nav-hud" :class="{ collapsed: !showNavControls }">
      <button
        class="nav-toggle-btn glass-panel"
        @click="showNavControls = !showNavControls"
        :title="showNavControls ? 'Hide Page Controls' : 'Show TV & Phone Navigation Controls'"
      >
        <span class="hud-toggle-icon">{{ showNavControls ? '▼' : '🎮' }}</span>
        <span class="hud-toggle-label">{{ showNavControls ? 'Hide' : 'Controls' }}</span>
      </button>

      <div v-if="showNavControls" class="nav-hud-body glass-panel">
        <!-- Directional D-Pad (Up, Down, Left, Right, Center) -->
        <div class="dpad-container">
          <button class="dpad-btn up" @click="panCanvas(0, 120)" title="Pan Up (▲)">
            ▲
          </button>
          <div class="dpad-row">
            <button class="dpad-btn left" @click="panCanvas(120, 0)" title="Pan Left (◀)">
              ◀
            </button>
            <button class="dpad-btn center" @click="fitToScreen" title="Center & Fit (🎯)">
              🎯
            </button>
            <button class="dpad-btn right" @click="panCanvas(-120, 0)" title="Pan Right (▶)">
              ▶
            </button>
          </div>
          <button class="dpad-btn down" @click="panCanvas(0, -120)" title="Pan Down (▼)">
            ▼
          </button>
        </div>

        <!-- Secondary Action Column: Zoom, Lock & Fullscreen -->
        <div class="nav-hud-actions">
          <button class="hud-action-btn" @click="zoomIn" title="Zoom In (+)">
            <span>+</span>
          </button>
          <button class="hud-action-btn" @click="zoomOut" title="Zoom Out (−)">
            <span>−</span>
          </button>
          <button
            class="hud-action-btn"
            :class="{ locked: isPositionLocked }"
            @click="togglePositionLock"
            :title="isPositionLocked ? 'Unlock canvas pan/zoom' : 'Lock position (ideal for wall tablets & TVs)'"
          >
            <span>{{ isPositionLocked ? '🔒' : '🔓' }}</span>
          </button>
          <button
            class="hud-action-btn"
            @click="toggleFullscreen"
            title="Toggle Fullscreen Mode (⛶)"
          >
            <span>{{ isFullscreen ? '⤓' : '⛶' }}</span>
          </button>
        </div>
      </div>
    </div>
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

.clear-trail-btn {
  color: #f87171;
}

.clear-trail-btn:hover {
  background: rgba(239, 68, 68, 0.15);
  color: #ef4444;
}

/* Site Overview Building Roll-Up Overlay */
.overview-rollups-overlay {
  position: absolute;
  top: 70px;
  left: 20px;
  width: 320px;
  max-height: calc(100vh - 160px);
  overflow-y: auto;
  padding: 14px;
  border-radius: var(--radius-md, 12px);
  z-index: 25;
  background: rgba(15, 23, 42, 0.88);
  border: 1px solid rgba(255, 255, 255, 0.12);
  backdrop-filter: blur(12px);
  box-shadow: 0 12px 36px rgba(0, 0, 0, 0.5);
}

.rollups-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.rollups-title {
  font-size: 13px;
  font-weight: 600;
  color: #ffffff;
}

.rollups-count {
  font-size: 11px;
  color: #94a3b8;
  background: rgba(255, 255, 255, 0.08);
  padding: 2px 8px;
  border-radius: 9999px;
}

.rollups-grid {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.building-rollup-card {
  padding: 12px;
  background: rgba(30, 41, 59, 0.7);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.building-rollup-card:hover {
  background: rgba(30, 41, 59, 0.95);
  border-color: #6366f1;
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.35);
}

.building-rollup-card.has-alert {
  border-color: rgba(239, 68, 68, 0.4);
  background: rgba(239, 68, 68, 0.08);
}

.b-card-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.b-name {
  font-size: 13px;
  font-weight: 600;
  color: #ffffff;
}

.b-status-pill {
  font-size: 10px;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 9999px;
  letter-spacing: 0.5px;
}

.pill-secure {
  background: rgba(16, 185, 129, 0.15);
  color: #34d399;
  border: 1px solid rgba(16, 185, 129, 0.3);
}

.pill-alert {
  background: rgba(239, 68, 68, 0.2);
  color: #f87171;
  border: 1px solid rgba(239, 68, 68, 0.4);
  animation: liveDotPulse 1.5s infinite;
}

.b-metrics {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 11px;
  margin-bottom: 8px;
}

.b-metric-row {
  display: flex;
  justify-content: space-between;
}

.m-label {
  color: #94a3b8;
}

.m-val {
  color: #cbd5e1;
  font-weight: 500;
}

.m-val.val-alert {
  color: #f87171;
  font-weight: 700;
}

.b-card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 10px;
  color: #64748b;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  padding-top: 6px;
}

.jump-arrow {
  color: #818cf8;
  font-weight: 600;
}

/* Motion Traversal Animations */
.traversal-animated-line {
  animation: motionDashFlow 1.2s linear infinite;
}

@keyframes motionDashFlow {
  to {
    stroke-dashoffset: -26;
  }
}

.occupant-lead-pulse {
  animation: occupantPulse 1.5s cubic-bezier(0.2, 0.8, 0.2, 1) infinite;
}

@keyframes occupantPulse {
  0% {
    r: 12;
    opacity: 0.9;
  }
  100% {
    r: 32;
    opacity: 0;
  }
}

/* Canvas Building Markers */
.overview-building-marker {
  cursor: pointer;
  transition: transform 0.2s ease;
}

.overview-building-marker:hover .building-box {
  filter: drop-shadow(0 0 12px rgba(99, 102, 241, 0.5));
}

/* Position Lock Visual State */
.live-container.position-locked {
  cursor: default !important;
}

.lock-btn.active {
  background: rgba(239, 68, 68, 0.25) !important;
  border-color: #ef4444 !important;
  color: #ffffff !important;
}

/* TV & Phone Navigation HUD */
.live-nav-hud {
  position: absolute;
  bottom: 24px;
  right: 24px;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 8px;
  z-index: 120;
  user-select: none;
}

.nav-toggle-btn {
  background: rgba(15, 23, 42, 0.85);
  border: 1px solid rgba(255, 255, 255, 0.15);
  color: var(--text-secondary);
  font-size: 11px;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: var(--radius-sm, 6px);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  transition: all 0.15s ease;
}

.nav-toggle-btn:hover {
  background: rgba(99, 102, 241, 0.25);
  color: #ffffff;
  border-color: #6366f1;
}

.nav-hud-body {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: rgba(15, 23, 42, 0.88);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: var(--radius-lg, 12px);
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.6);
  animation: fadeIn 0.2s ease;
}

/* Directional D-Pad */
.dpad-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
}

.dpad-row {
  display: flex;
  align-items: center;
  gap: 3px;
}

.dpad-btn {
  width: 34px;
  height: 34px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: var(--radius-sm, 6px);
  color: var(--text-primary, #ffffff);
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.15s ease;
}

.dpad-btn:hover {
  background: rgba(99, 102, 241, 0.35);
  border-color: #6366f1;
  color: #ffffff;
  transform: scale(1.05);
}

.dpad-btn:active {
  transform: scale(0.95);
  background: #6366f1;
}

.dpad-btn.center {
  background: rgba(99, 102, 241, 0.2);
  border-color: rgba(99, 102, 241, 0.4);
  font-size: 14px;
}

/* Secondary Actions (Zoom, Lock, Fullscreen) */
.nav-hud-actions {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.hud-action-btn {
  width: 32px;
  height: 32px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: var(--radius-sm, 6px);
  color: var(--text-secondary, #cbd5e1);
  font-size: 14px;
  font-weight: bold;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.15s ease;
}

.hud-action-btn:hover {
  background: rgba(255, 255, 255, 0.15);
  color: #ffffff;
}

.hud-action-btn.locked {
  background: rgba(239, 68, 68, 0.25);
  border-color: #ef4444;
  color: #ffffff;
}

/* Responsive Overlays for Phones & Tablets */
@media (max-width: 768px) {
  .live-floating-bar {
    top: 10px;
    padding: 4px 8px;
    gap: 4px;
    flex-wrap: wrap;
    max-width: 95vw;
  }

  .live-control-btn {
    font-size: 11px;
    padding: 4px 8px;
  }

  .live-nav-hud {
    bottom: 16px;
    right: 16px;
  }

  .dpad-btn {
    width: 38px;
    height: 38px;
  }

  .hud-action-btn {
    width: 36px;
    height: 36px;
  }

  .overview-rollups-overlay {
    top: auto;
    bottom: 12px;
    left: 12px;
    right: 12px;
    max-height: 40vh;
    overflow-y: auto;
  }
}
</style>
