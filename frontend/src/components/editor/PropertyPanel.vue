<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from "vue";
import { useEditorStore } from "@/stores/editorStore";
import { usePlanStore } from "@/stores/planStore";
import { useEntityStore } from "@/stores/entityStore";
import type { EndpointType, SubArea } from "@/types/plan";

const editorStore = useEditorStore();
const planStore = usePlanStore();
const entityStore = useEntityStore();

const multiGroupName = ref("");
const newSubAreaName = ref("");
const newSubAreaParent = ref("");

const isMultiSelect = computed(() => editorStore.selectedEndpointIds.length > 1);

const selectedEndpoint = computed(() => {
  if (editorStore.selectedEndpointIds.length !== 1) return null;
  return planStore.currentEndpoints.find((ep) => ep.id === editorStore.selectedEndpointId) || null;
});

const selectedShape = computed(() => {
  if (!editorStore.selectedShapeId) return null;
  return planStore.currentShapes.find((s) => s.id === editorStore.selectedShapeId) || null;
});

function handleWallThickness(e: Event) {
  const target = e.target as HTMLInputElement;
  const val = parseInt(target.value, 10);
  if (selectedShape.value && !isNaN(val)) {
    const geom = { ...selectedShape.value.geometry, thickness: val };
    planStore.updateShape(selectedShape.value.id, { geometry: geom });
  }
}

function handleShapeStroke(e: Event) {
  const target = e.target as HTMLInputElement;
  if (selectedShape.value) {
    const style = { ...selectedShape.value.style, stroke: target.value };
    planStore.updateShape(selectedShape.value.id, { style });
  }
}

function handleRoomName(e: Event) {
  const target = e.target as HTMLInputElement;
  if (selectedShape.value && selectedShape.value.type === "room") {
    const geom = { ...selectedShape.value.geometry, name: target.value };
    planStore.updateShape(selectedShape.value.id, { geometry: geom });
  }
}

function handleLabelText(e: Event) {
  const target = e.target as HTMLInputElement;
  if (selectedShape.value && selectedShape.value.type === "label") {
    const geom = { ...selectedShape.value.geometry, text: target.value };
    planStore.updateShape(selectedShape.value.id, { geometry: geom });
  }
}

function deleteCurrentShape() {
  if (selectedShape.value) {
    planStore.removeShape(selectedShape.value.id);
    editorStore.selectedShapeId = null;
  }
}

function deleteWallOpening(openingId: string) {
  if (selectedShape.value && selectedShape.value.type === "wall") {
    planStore.removeWallOpening(selectedShape.value.id, openingId);
  }
}

// Other endpoints on the floor that can act as a parent for nesting
const availableParentEndpoints = computed(() => {
  if (!selectedEndpoint.value) return [];
  return planStore.currentEndpoints.filter((ep) => ep.id !== selectedEndpoint.value?.id);
});

const endpointTypes: { label: string; value: EndpointType }[] = [
  { label: "Door", value: "door" },
  { label: "Window", value: "window" },
  { label: "Motion Sensor", value: "motion" },
  { label: "Camera", value: "camera" },
  { label: "Generic Sensor", value: "generic" },
];

function updateType(e: Event) {
  const target = e.target as HTMLSelectElement;
  if (selectedEndpoint.value) {
    planStore.updateEndpoint(selectedEndpoint.value.id, { type: target.value as EndpointType });
  }
}

function updateLabel(e: Event) {
  const target = e.target as HTMLInputElement;
  if (selectedEndpoint.value) {
    planStore.updateEndpoint(selectedEndpoint.value.id, { label: target.value });
  }
}

function updateRotation(e: Event) {
  const target = e.target as HTMLInputElement;
  if (selectedEndpoint.value) {
    planStore.updateEndpoint(selectedEndpoint.value.id, { rotation: Number(target.value) });
  }
}

function stepRotate(delta: number) {
  if (!selectedEndpoint.value) return;
  const current = selectedEndpoint.value.rotation || 0;
  const next = (current + delta + 360) % 360;
  planStore.updateEndpoint(selectedEndpoint.value.id, { rotation: next });
}

function handleParentChange(e: Event) {
  const target = e.target as HTMLSelectElement;
  const parentId = target.value || null;
  if (selectedEndpoint.value) {
    planStore.nestEndpoint(selectedEndpoint.value.id, parentId);
  }
}

function handleSingleGroupName(e: Event) {
  const target = e.target as HTMLInputElement;
  if (selectedEndpoint.value) {
    planStore.updateEndpoint(selectedEndpoint.value.id, {
      group_name: target.value.trim() || null,
      group_id: target.value.trim() ? (selectedEndpoint.value.group_id || "grp_" + Math.random().toString(36).substring(2, 8)) : null,
    });
  }
}

function removeSingleFromGroup() {
  if (selectedEndpoint.value) {
    planStore.updateEndpoint(selectedEndpoint.value.id, {
      group_id: null,
      group_name: null,
    });
  }
}

function handleGroupSelection() {
  const name = multiGroupName.value.trim() || "Grouped Unit";
  planStore.groupEndpoints(editorStore.selectedEndpointIds, name);
  multiGroupName.value = "";
}

function handleUngroupSelection() {
  planStore.ungroupEndpoints(editorStore.selectedEndpointIds);
}

function deleteSelection() {
  if (confirm(`Delete ${editorStore.selectedEndpointIds.length} selected endpoints?`)) {
    for (const id of [...editorStore.selectedEndpointIds]) {
      planStore.removeEndpoint(id);
    }
    editorStore.clearSelection();
  }
}

function deleteEndpoint() {
  if (selectedEndpoint.value && confirm("Delete this endpoint from the floor plan?")) {
    planStore.removeEndpoint(selectedEndpoint.value.id);
    editorStore.clearSelection();
  }
}

function handleCreateSubArea() {
  if (!newSubAreaName.value.trim()) return;
  const newSubArea: SubArea = {
    id: "sub_" + Math.random().toString(36).substring(2, 9),
    name: newSubAreaName.value.trim(),
    parent_area_id: newSubAreaParent.value || null,
    x: 100,
    y: 100,
    width: 200,
    height: 150,
  };
  planStore.addSubArea(newSubArea);
  newSubAreaName.value = "";
  newSubAreaParent.value = "";
}

function deleteSubArea(id: string) {
  if (confirm("Remove this sub-area/zone?")) {
    planStore.removeSubArea(id);
  }
}

// 1. Orphan Entity Detection (Missing from HA)
const isEntityOrphaned = computed(() => {
  if (!selectedEndpoint.value) return false;
  if (selectedEndpoint.value.type === "composite") return false;
  return !entityStore.isKnownEntity(selectedEndpoint.value.entity_id);
});

function updateEntityId(e: Event) {
  const target = e.target as HTMLInputElement;
  if (!selectedEndpoint.value) return;
  const newEid = target.value.trim();
  if (newEid) {
    planStore.updateEndpoint(selectedEndpoint.value.id, { entity_id: newEid });
  }
}

function removeAttachment() {
  if (selectedEndpoint.value) {
    planStore.updateEndpoint(selectedEndpoint.value.id, { attached_to: null });
  }
}

// 2. Companion Entities Management (Spec §Endpoints)
const selectedCompanionToAdd = ref("");

const availableEntitiesForCompanions = computed(() => {
  if (!selectedEndpoint.value) return [];
  const current = selectedEndpoint.value.companions || [];
  return entityStore.entities.filter(
    (e) => e.entity_id !== selectedEndpoint.value?.entity_id && !current.includes(e.entity_id)
  );
});

function addCompanion(eid: string) {
  if (!selectedEndpoint.value || !eid) return;
  const current = [...(selectedEndpoint.value.companions || [])];
  if (!current.includes(eid)) {
    current.push(eid);
    planStore.updateEndpoint(selectedEndpoint.value.id, { companions: current });
  }
  selectedCompanionToAdd.value = "";
}

function removeCompanion(eid: string) {
  if (!selectedEndpoint.value) return;
  const current = (selectedEndpoint.value.companions || []).filter((c) => c !== eid);
  planStore.updateEndpoint(selectedEndpoint.value.id, { companions: current });
}

function autoDetectCompanions() {
  if (!selectedEndpoint.value) return;
  const baseEid = selectedEndpoint.value.entity_id;
  const parts = baseEid.split(".");
  const domain = parts[0];
  const name = parts.slice(1).join(".");

  const detected: string[] = [];
  const suffixes = ["_battery", "_caution", "_problem", "_low_battery", "_tamper", "_temperature"];

  for (const ent of entityStore.entities) {
    if (ent.entity_id === baseEid) continue;
    for (const s of suffixes) {
      if (ent.entity_id.includes(name + s) || ent.entity_id.startsWith(`${domain}.${name}${s}`)) {
        if (!detected.includes(ent.entity_id)) {
          detected.push(ent.entity_id);
        }
      }
    }
  }

  if (detected.length > 0) {
    const existing = selectedEndpoint.value.companions || [];
    const merged = Array.from(new Set([...existing, ...detected]));
    planStore.updateEndpoint(selectedEndpoint.value.id, { companions: merged });
    alert(`Auto-detected ${detected.length} companion sensor(s):\n${detected.join("\n")}`);
  } else {
    alert(`No companion sensors found matching pattern '${name}_[battery/caution/problem]'. You can add companions manually from the dropdown.`);
  }
}

// 3. Linked Cameras Management (Spec §Endpoints)
const selectedCameraToAdd = ref("");

const availableCameras = computed(() => {
  const list: Array<{ id: string; label: string }> = [];
  // From placed endpoints
  for (const ep of planStore.currentEndpoints) {
    if (ep.type === "camera") {
      list.push({ id: ep.entity_id, label: `${ep.label || ep.entity_id} (Placed)` });
    }
  }
  // From HA camera entities
  for (const ent of entityStore.entities) {
    if (ent.domain === "camera" || ent.entity_id.startsWith("camera.")) {
      if (!list.some((c) => c.id === ent.entity_id)) {
        list.push({ id: ent.entity_id, label: ent.friendly_name || ent.entity_id });
      }
    }
  }
  return list;
});

function addLinkedCamera(camEid: string) {
  if (!selectedEndpoint.value || !camEid) return;
  const current = [...(selectedEndpoint.value.cameras || [])];
  if (!current.includes(camEid)) {
    current.push(camEid);
    planStore.updateEndpoint(selectedEndpoint.value.id, { cameras: current });
  }
  selectedCameraToAdd.value = "";
}

function removeLinkedCamera(camEid: string) {
  if (!selectedEndpoint.value) return;
  const current = (selectedEndpoint.value.cameras || []).filter((c) => c !== camEid);
  planStore.updateEndpoint(selectedEndpoint.value.id, { cameras: current });
}

// 4. Stale Sensor Threshold
function updateStaleAfter(e: Event) {
  const target = e.target as HTMLSelectElement;
  if (selectedEndpoint.value) {
    planStore.updateEndpoint(selectedEndpoint.value.id, {
      stale_after: target.value.trim() ? target.value.trim() : null,
    });
  }
}

// 5. Coverage Cone FOV Controls
function toggleCoverage(e: Event) {
  const target = e.target as HTMLInputElement;
  if (!selectedEndpoint.value) return;
  if (target.checked) {
    const defaultRange = selectedEndpoint.value.type === "camera" ? 120 : 75;
    const defaultAngle = selectedEndpoint.value.type === "camera" ? 70 : 85;
    planStore.updateEndpoint(selectedEndpoint.value.id, {
      coverage: { type: "cone", range: defaultRange, angle: defaultAngle },
    });
  } else {
    planStore.updateEndpoint(selectedEndpoint.value.id, { coverage: null });
  }
}

function updateCoverageRange(e: Event) {
  const target = e.target as HTMLInputElement;
  if (!selectedEndpoint.value) return;
  const range = parseInt(target.value, 10);
  const currentCoverage = selectedEndpoint.value.coverage || {
    type: "cone",
    range: 120,
    angle: selectedEndpoint.value.type === "camera" ? 70 : 85,
  };
  planStore.updateEndpoint(selectedEndpoint.value.id, {
    coverage: { ...currentCoverage, range },
  });
}

function updateCoverageAngle(e: Event) {
  const target = e.target as HTMLInputElement;
  if (!selectedEndpoint.value) return;
  const angle = parseInt(target.value, 10);
  const currentCoverage = selectedEndpoint.value.coverage || {
    type: "cone",
    range: selectedEndpoint.value.type === "camera" ? 120 : 75,
    angle: 70,
  };
  planStore.updateEndpoint(selectedEndpoint.value.id, {
    coverage: { ...currentCoverage, angle },
  });
}

// Docking, minimize, and free move state
export type PropsDockMode = "right" | "left" | "float";
const dockMode = ref<PropsDockMode>(getInitialPropsDock());
const isMinimized = ref<boolean>(localStorage.getItem("sh_props_min") === "true");
const floatPos = ref<{ x: number; y: number }>(getInitialPropsPos());
const isDraggingHeader = ref(false);

function getInitialPropsDock(): PropsDockMode {
  try {
    const saved = localStorage.getItem("sh_props_dock");
    if (saved && ["right", "left", "float"].includes(saved)) {
      return saved as PropsDockMode;
    }
  } catch {}
  return "right";
}

function getInitialPropsPos(): { x: number; y: number } {
  try {
    const saved = localStorage.getItem("sh_props_pos");
    if (saved) {
      const parsed = JSON.parse(saved);
      if (typeof parsed.x === "number" && typeof parsed.y === "number") {
        return parsed;
      }
    }
  } catch {}
  return { x: typeof window !== "undefined" ? Math.max(20, window.innerWidth - 320) : 1000, y: 72 };
}

function setDockMode(mode: PropsDockMode) {
  dockMode.value = mode;
  try {
    localStorage.setItem("sh_props_dock", mode);
  } catch {}
}

function cycleDockMode() {
  const modes: PropsDockMode[] = ["right", "left", "float"];
  const next = modes[(modes.indexOf(dockMode.value) + 1) % modes.length];
  setDockMode(next);
}

function toggleMinimize() {
  isMinimized.value = !isMinimized.value;
  try {
    localStorage.setItem("sh_props_min", String(isMinimized.value));
  } catch {}
}

function startHeaderDrag(e: MouseEvent) {
  isDraggingHeader.value = true;
  const startClientX = e.clientX;
  const startClientY = e.clientY;
  const origDockMode = dockMode.value;
  let origX = floatPos.value.x;
  let origY = floatPos.value.y;
  let hasMoved = false;

  const onMouseMove = (ev: MouseEvent) => {
    const dx = ev.clientX - startClientX;
    const dy = ev.clientY - startClientY;
    if (!hasMoved && Math.hypot(dx, dy) > 3) {
      hasMoved = true;
      if (origDockMode !== "float") {
        setDockMode("float");
        origX = Math.max(10, Math.min(window.innerWidth - 310, startClientX - 150));
        origY = Math.max(10, Math.min(window.innerHeight - 100, startClientY - 20));
      }
    }
    if (hasMoved || origDockMode === "float") {
      floatPos.value = {
        x: Math.max(10, Math.min(window.innerWidth - 310, origX + dx)),
        y: Math.max(10, Math.min(window.innerHeight - 80, origY + dy)),
      };
    }
  };

  const onMouseUp = () => {
    isDraggingHeader.value = false;
    window.removeEventListener("mousemove", onMouseMove);
    window.removeEventListener("mouseup", onMouseUp);
    try {
      localStorage.setItem("sh_props_pos", JSON.stringify(floatPos.value));
    } catch {}
  };

  window.addEventListener("mousemove", onMouseMove);
  window.addEventListener("mouseup", onMouseUp);
}

function onWorkspacePreset(e: Event) {
  const detail = (e as CustomEvent).detail;
  if (!detail) return;
  if (detail.preset === "cad" || detail.preset === "zen") {
    isMinimized.value = true;
  } else if (detail.preset === "mapping") {
    isMinimized.value = false;
    setDockMode("right");
  }
}

onMounted(() => {
  window.addEventListener("sh-workspace-preset", onWorkspacePreset);
});

onUnmounted(() => {
  window.removeEventListener("sh-workspace-preset", onWorkspacePreset);
});
</script>

<template>
  <!-- Minimized Floating Pill -->
  <div
    v-if="isMinimized"
    :class="['props-minimized-pill', 'glass-panel', `dock-${dockMode}`]"
    :style="dockMode === 'float' ? { left: `${floatPos.x}px`, top: `${floatPos.y}px` } : undefined"
    @mousedown="startHeaderDrag"
    @click="toggleMinimize"
    title="Click to restore Properties & Floor Areas panel (drag to move)"
  >
    <span class="pill-icon">📐</span>
    <span class="pill-text">Properties & Zones</span>
    <span class="pill-badge" v-if="editorStore.selectedEndpointIds.length > 0">
      {{ editorStore.selectedEndpointIds.length }}
    </span>
    <button class="pill-action-btn" @click.stop="cycleDockMode" :title="`Docked: ${dockMode.toUpperCase()}. Click to cycle.`">
      ⚓
    </button>
    <button class="pill-action-btn" @click.stop="toggleMinimize" title="Expand panel">
      ▲
    </button>
  </div>

  <!-- Multi-Selection Mode -->
  <aside
    v-else-if="isMultiSelect"
    :class="['property-panel', 'glass-panel', `dock-${dockMode}`]"
    :style="dockMode === 'float' ? { left: `${floatPos.x}px`, top: `${floatPos.y}px` } : undefined"
  >
    <div class="panel-header" @mousedown="startHeaderDrag">
      <div class="header-title">
        <span>Selection</span>
        <span class="count-badge">{{ editorStore.selectedEndpointIds.length }} items</span>
      </div>
      <div class="panel-header-actions" @mousedown.stop>
        <button
          class="panel-tool-btn"
          :title="`Dock: ${dockMode.toUpperCase()}. Click to cycle (Right, Left, Float)`"
          @click="cycleDockMode"
        >
          ⚓ {{ dockMode.toUpperCase() }}
        </button>
        <button class="panel-tool-btn" title="Minimize panel" @click="toggleMinimize">─</button>
        <button class="close-btn" @click="editorStore.clearSelection()">×</button>
      </div>
    </div>

    <div class="panel-body">
      <div class="tip-card">
        💡 <strong>Tip:</strong> Drag any selected endpoint to move all {{ editorStore.selectedEndpointIds.length }} items together across the canvas.
      </div>

      <!-- Group into Unit -->
      <div class="prop-group">
        <label>Group Into Unit</label>
        <p class="field-help">Combine selected entities into a single logical unit.</p>
        <input
          type="text"
          v-model="multiGroupName"
          placeholder="e.g. Master Suite or Entryway Zone"
        />
        <button class="primary-action-btn" @click="handleGroupSelection">
          🔗 Group as Single Unit
        </button>
      </div>

      <div class="divider"></div>

      <!-- Ungroup -->
      <div class="prop-group">
        <button class="secondary-action-btn" @click="handleUngroupSelection">
          🔓 Ungroup Selected Items
        </button>
      </div>

      <!-- Bulk Delete -->
      <div class="panel-actions">
        <button class="delete-btn" @click="deleteSelection">
          <svg viewBox="0 0 24 24" width="16" height="16">
            <path fill="currentColor" d="M19,4H15.5L14.5,3H9.5L8.5,4H5V6H19M6,19A2,2 0 0,0 8,21H16A2,2 0 0,0 18,19V7H6V19Z"/>
          </svg>
          Delete Selected ({{ editorStore.selectedEndpointIds.length }})
        </button>
      </div>
    </div>
  </aside>

  <!-- Single Endpoint Selected -->
  <aside
    v-else-if="selectedEndpoint"
    :class="['property-panel', 'glass-panel', `dock-${dockMode}`]"
    :style="dockMode === 'float' ? { left: `${floatPos.x}px`, top: `${floatPos.y}px` } : undefined"
  >
    <div class="panel-header" @mousedown="startHeaderDrag">
      <div class="header-title">Endpoint Properties</div>
      <div class="panel-header-actions" @mousedown.stop>
        <button
          class="panel-tool-btn"
          :title="`Dock: ${dockMode.toUpperCase()}. Click to cycle (Right, Left, Float)`"
          @click="cycleDockMode"
        >
          ⚓ {{ dockMode.toUpperCase() }}
        </button>
        <button class="panel-tool-btn" title="Minimize panel" @click="toggleMinimize">─</button>
        <button class="close-btn" @click="editorStore.clearSelection()">×</button>
      </div>
    </div>

    <div class="panel-body">
      <!-- Label -->
      <div class="prop-group">
        <label>Display Label</label>
        <input
          type="text"
          :value="selectedEndpoint.label"
          @input="updateLabel"
          placeholder="e.g. Front Door Motion"
        />
      </div>

      <!-- Type (Door vs Window distinction) -->
      <div class="prop-group">
        <label>Endpoint Type</label>
        <select :value="selectedEndpoint.type" @change="updateType">
          <option v-for="t in endpointTypes" :key="t.value" :value="t.value">
            {{ t.label }}
          </option>
        </select>
      </div>

      <!-- Attached To -->
      <div class="prop-group">
        <label>Attached To</label>
        <div v-if="selectedEndpoint.attached_to" class="attached-badge">
          <span class="attachment-icon">🔗</span>
          <span class="attachment-text">{{ selectedEndpoint.attached_to.type.charAt(0).toUpperCase() + selectedEndpoint.attached_to.type.slice(1) }}</span>
          <button class="remove-attachment-btn" @click="removeAttachment" title="Detach from shape">×</button>
        </div>
        <div v-else class="unattached-text">
          <span class="field-help">Not attached. Drag near a wall, room edge, door, or window to attach.</span>
        </div>
      </div>

      <!-- Rotation with slider and 90° quick buttons -->
      <div class="prop-group">
        <div class="prop-row-header">
          <label>Orientation & Rotation</label>
          <span class="value-badge">{{ selectedEndpoint.rotation || 0 }}°</span>
        </div>
        <div class="rotation-controls">
          <button class="rotate-step-btn" title="Rotate -90°" @click="stepRotate(-90)">↺ -90°</button>
          <input
            type="range"
            min="0"
            max="359"
            :value="selectedEndpoint.rotation || 0"
            @input="updateRotation"
            class="rotate-slider"
          />
          <button class="rotate-step-btn" title="Rotate +90°" @click="stepRotate(90)">↻ +90°</button>
        </div>
      </div>

      <!-- Entity ID (Editable) -->
      <div class="prop-group">
        <label>Entity ID</label>
        <input
          type="text"
          :value="selectedEndpoint.entity_id"
          @change="updateEntityId"
          placeholder="e.g. camera.living_room or binary_sensor.front_door"
        />
        <p class="field-help">Home Assistant entity ID providing states and video/snapshots.</p>
      </div>

      <!-- Orphan Entity Warning (Spec §Editing behaviour) -->
      <div v-if="isEntityOrphaned" class="warning-alert-box">
        <div class="alert-title">⚠️ Entity Not Found in HA</div>
        <p class="alert-desc">
          This entity ID is not currently registered in Home Assistant. Real-time updates will not be received.
        </p>
      </div>

      <!-- Companion Entities (Spec §Endpoints & §First site reference) -->
      <div class="prop-group">
        <div class="prop-row-header">
          <label>Companion Sensors ({{ (selectedEndpoint.companions || []).length }})</label>
          <button
            type="button"
            class="auto-detect-btn"
            title="Scan Home Assistant for matching battery/caution sensors"
            @click="autoDetectCompanions"
          >
            ⚡ Auto-Detect
          </button>
        </div>
        <p class="field-help">Attach battery or caution sensors displayed as endpoint badges.</p>

        <!-- Current companions list -->
        <div v-if="selectedEndpoint.companions?.length" class="items-chip-list">
          <div v-for="comp in selectedEndpoint.companions" :key="comp" class="chip-item">
            <span class="chip-text">{{ comp }}</span>
            <button class="chip-remove" title="Remove companion" @click="removeCompanion(comp)">×</button>
          </div>
        </div>

        <!-- Add companion picker -->
        <div class="add-item-row" v-if="availableEntitiesForCompanions.length">
          <select v-model="selectedCompanionToAdd">
            <option value="">+ Add companion sensor...</option>
            <option v-for="ent in availableEntitiesForCompanions" :key="ent.entity_id" :value="ent.entity_id">
              {{ ent.friendly_name || ent.entity_id }}
            </option>
          </select>
          <button
            class="add-item-btn"
            :disabled="!selectedCompanionToAdd"
            @click="addCompanion(selectedCompanionToAdd)"
          >
            Add
          </button>
        </div>
      </div>

      <!-- Linked Cameras (Spec §Endpoints & §Cameras) -->
      <div class="prop-group" v-if="selectedEndpoint.type !== 'camera'">
        <label>Linked Cameras ({{ (selectedEndpoint.cameras || []).length }})</label>
        <p class="field-help">Automatically open camera snapshot popup when this sensor fires.</p>

        <!-- Current linked cameras list -->
        <div v-if="selectedEndpoint.cameras?.length" class="items-chip-list">
          <div v-for="cam in selectedEndpoint.cameras" :key="cam" class="chip-item camera-chip">
            <span class="chip-text">📹 {{ cam }}</span>
            <button class="chip-remove" title="Unlink camera" @click="removeLinkedCamera(cam)">×</button>
          </div>
        </div>

        <!-- Add linked camera picker -->
        <div class="add-item-row" v-if="availableCameras.length">
          <select v-model="selectedCameraToAdd">
            <option value="">+ Link a camera feed...</option>
            <option v-for="cam in availableCameras" :key="cam.id" :value="cam.id">
              {{ cam.label }}
            </option>
          </select>
          <button
            class="add-item-btn"
            :disabled="!selectedCameraToAdd"
            @click="addLinkedCamera(selectedCameraToAdd)"
          >
            Link
          </button>
        </div>
      </div>

      <!-- Stale RF Sensor Threshold (Spec §Last seen) -->
      <div class="prop-group">
        <label>Stale RF Sensor Flagging</label>
        <p class="field-help">Flag sensor with a warning badge if no state change occurs within this window.</p>
        <select :value="selectedEndpoint.stale_after || ''" @change="updateStaleAfter">
          <option value="">Disabled (Real-time)</option>
          <option value="1h">1 hour</option>
          <option value="6h">6 hours</option>
          <option value="12h">12 hours</option>
          <option value="24h">24 hours (1 day)</option>
          <option value="3d">3 days</option>
          <option value="7d">7 days (1 week)</option>
          <option value="30d">30 days (1 month)</option>
        </select>
      </div>

      <!-- Coverage Cone / Field of View (Spec §Coverage) -->
      <div class="prop-group" v-if="selectedEndpoint.type === 'motion' || selectedEndpoint.type === 'camera'">
        <div class="prop-row-header">
          <label>{{ selectedEndpoint.type === 'camera' ? 'Camera Field of View & Depth' : 'Detection / Coverage FOV' }}</label>
          <label class="toggle-switch">
            <input
              type="checkbox"
              :checked="!!selectedEndpoint.coverage || selectedEndpoint.type === 'camera'"
              @change="toggleCoverage"
            />
            <span class="toggle-slider"></span>
          </label>
        </div>
        <p class="field-help">
          {{ selectedEndpoint.type === 'camera' ? 'Adjust camera depth of view (distance) and field-of-view angle on the floor plan.' : 'Visual field-of-view or PIR detection sector on the floor plan.' }}
        </p>

        <div v-if="selectedEndpoint.coverage || selectedEndpoint.type === 'camera'" class="coverage-controls-box">
          <div class="slider-row">
            <div class="slider-info">
              <span>Depth of View (Range)</span>
              <span class="val-tag">{{ (selectedEndpoint.coverage?.range ?? (selectedEndpoint.type === 'camera' ? 120 : 75)) }}px</span>
            </div>
            <input
              type="range"
              min="30"
              max="500"
              step="5"
              :value="selectedEndpoint.coverage?.range ?? (selectedEndpoint.type === 'camera' ? 120 : 75)"
              @input="updateCoverageRange"
              class="range-slider"
            />
          </div>

          <div class="slider-row">
            <div class="slider-info">
              <span>Field of View (Angle)</span>
              <span class="val-tag">{{ (selectedEndpoint.coverage?.angle ?? (selectedEndpoint.type === 'camera' ? 70 : 85)) }}°</span>
            </div>
            <input
              type="range"
              min="15"
              max="180"
              step="5"
              :value="selectedEndpoint.coverage?.angle ?? (selectedEndpoint.type === 'camera' ? 70 : 85)"
              @input="updateCoverageAngle"
              class="range-slider"
            />
          </div>
        </div>
      </div>

      <!-- Group Unit -->
      <div class="prop-group">
        <label>Group Unit</label>
        <p class="field-help">Assign this endpoint to a group or unit.</p>
        <div class="group-row">
          <input
            type="text"
            :value="selectedEndpoint.group_name || ''"
            @change="handleSingleGroupName"
            placeholder="e.g. Entryway Sensors"
          />
          <button
            v-if="selectedEndpoint.group_id"
            class="tiny-btn danger"
            title="Remove from group"
            @click="removeSingleFromGroup"
          >
            Ungroup
          </button>
        </div>
      </div>

      <!-- Nesting: Entity within an entity -->
      <div class="prop-group">
        <label>Nest Within Parent Entity</label>
        <p class="field-help">Attach to another entity (e.g. sensor on door or camera).</p>
        <select :value="selectedEndpoint.parent_id || ''" @change="handleParentChange">
          <option value="">Independent (Root Entity)</option>
          <option v-for="p in availableParentEndpoints" :key="p.id" :value="p.id">
            ↳ {{ p.label || p.entity_id }} ({{ p.type }})
          </option>
        </select>
      </div>

      <!-- Position -->
      <div class="prop-row">
        <div class="prop-group">
          <label>X Position</label>
          <input type="number" :value="Math.round(selectedEndpoint.x)" readonly class="readonly-input" />
        </div>
        <div class="prop-group">
          <label>Y Position</label>
          <input type="number" :value="Math.round(selectedEndpoint.y)" readonly class="readonly-input" />
        </div>
      </div>

      <!-- Actions -->
      <div class="panel-actions">
        <button class="delete-btn" @click="deleteEndpoint">
          <svg viewBox="0 0 24 24" width="16" height="16">
            <path fill="currentColor" d="M19,4H15.5L14.5,3H9.5L8.5,4H5V6H19M6,19A2,2 0 0,0 8,21H16A2,2 0 0,0 18,19V7H6V19Z"/>
          </svg>
          Delete Endpoint
        </button>
      </div>
    </div>
  </aside>

  <!-- Single Shape Selected (Wall, Room, Label) -->
  <aside
    v-else-if="selectedShape"
    :class="['property-panel', 'glass-panel', `dock-${dockMode}`]"
    :style="dockMode === 'float' ? { left: `${floatPos.x}px`, top: `${floatPos.y}px` } : undefined"
  >
    <div class="panel-header" @mousedown="startHeaderDrag">
      <div class="header-title">{{ selectedShape.type.toUpperCase() }} Properties</div>
      <div class="panel-header-actions" @mousedown.stop>
        <button
          class="panel-tool-btn"
          :title="`Dock: ${dockMode.toUpperCase()}. Click to cycle (Right, Left, Float)`"
          @click="cycleDockMode"
        >
          ⚓ {{ dockMode.toUpperCase() }}
        </button>
        <button class="panel-tool-btn" title="Minimize panel" @click="toggleMinimize">─</button>
        <button class="close-btn" @click="editorStore.clearSelection()">×</button>
      </div>
    </div>

    <div class="panel-body">
      <!-- Wall properties -->
      <template v-if="selectedShape.type === 'wall'">
        <div class="prop-group">
          <label>Wall Thickness (px)</label>
          <input
            type="number"
            min="2"
            max="32"
            :value="(selectedShape.geometry as any).thickness || 8"
            @change="handleWallThickness"
          />
        </div>
        <div class="prop-group">
          <label>Wall Color</label>
          <input
            type="color"
            :value="(selectedShape.style as any).stroke || '#94a3b8'"
            @change="handleShapeStroke"
          />
        </div>
        <!-- Openings list -->
        <div class="prop-group" v-if="(selectedShape.geometry as any).openings?.length">
          <label>Wall Openings ({{ (selectedShape.geometry as any).openings.length }})</label>
          <div v-for="op in (selectedShape.geometry as any).openings" :key="op.id" class="subarea-row">
            <span class="subarea-name">{{ op.type === 'door' ? '🚪 Door Cutout' : '🪟 Window Cutout' }} ({{ op.width }}px)</span>
            <button class="tiny-btn danger" title="Remove opening" @click="deleteWallOpening(op.id)">×</button>
          </div>
        </div>
      </template>

      <!-- Room properties -->
      <template v-else-if="selectedShape.type === 'room'">
        <div class="prop-group">
          <label>Room Name</label>
          <input
            type="text"
            :value="(selectedShape.geometry as any).name || ''"
            @input="handleRoomName"
            placeholder="e.g. Master Bedroom"
          />
        </div>
        <div class="prop-group">
          <label>Border Color</label>
          <input
            type="color"
            :value="(selectedShape.style as any).stroke || '#6366f1'"
            @change="handleShapeStroke"
          />
        </div>
      </template>

      <!-- Label properties -->
      <template v-else-if="selectedShape.type === 'label'">
        <div class="prop-group">
          <label>Label Text</label>
          <input
            type="text"
            :value="(selectedShape.geometry as any).text || ''"
            @input="handleLabelText"
            placeholder="e.g. Patio"
          />
        </div>
      </template>

      <div class="panel-actions">
        <button class="delete-btn" @click="deleteCurrentShape">
          <svg viewBox="0 0 24 24" width="16" height="16">
            <path fill="currentColor" d="M19,4H15.5L14.5,3H9.5L8.5,4H5V6H19M6,19A2,2 0 0,0 8,21H16A2,2 0 0,0 18,19V7H6V19Z"/>
          </svg>
          Delete Shape
        </button>
      </div>
    </div>
  </aside>

  <!-- Default Floor / Sub-Area Management Panel -->
  <aside
    v-else
    :class="['property-panel', 'glass-panel', `dock-${dockMode}`]"
    :style="dockMode === 'float' ? { left: `${floatPos.x}px`, top: `${floatPos.y}px` } : undefined"
  >
    <div class="panel-header" @mousedown="startHeaderDrag">
      <div class="header-title">Floor Areas & Zones</div>
      <div class="panel-header-actions" @mousedown.stop>
        <button
          class="panel-tool-btn"
          :title="`Dock: ${dockMode.toUpperCase()}. Click to cycle (Right, Left, Float)`"
          @click="cycleDockMode"
        >
          ⚓ {{ dockMode.toUpperCase() }}
        </button>
        <button class="panel-tool-btn" title="Minimize panel" @click="toggleMinimize">─</button>
      </div>
    </div>

    <div class="panel-body">
      <!-- Create Sub-Area (Area within an area) -->
      <div class="prop-group">
        <label>Add Sub-Area / Zone</label>
        <p class="field-help">Define rooms or nested zones inside larger areas.</p>
        <input
          type="text"
          v-model="newSubAreaName"
          placeholder="Sub-area name (e.g. Walk-in Closet)"
          @keydown.enter="handleCreateSubArea"
        />
        <select v-if="entityStore.areas.length > 0" v-model="newSubAreaParent">
          <option value="">No Parent (Root Zone)</option>
          <option v-for="a in entityStore.areas" :key="a.area_id" :value="a.area_id">
            Parent Area: {{ a.name }}
          </option>
        </select>
        <button class="primary-action-btn" :disabled="!newSubAreaName.trim()" @click="handleCreateSubArea">
          + Add Sub-Area to Floor
        </button>
      </div>

      <!-- Current Sub-Areas List -->
      <div class="subareas-list" v-if="planStore.currentSubAreas.length > 0">
        <label>Configured Sub-Areas ({{ planStore.currentSubAreas.length }})</label>
        <div v-for="sa in planStore.currentSubAreas" :key="sa.id" class="subarea-row">
          <div class="subarea-info">
            <span class="subarea-name">{{ sa.name }}</span>
            <span v-if="sa.parent_area_id" class="parent-tag">nested</span>
          </div>
          <button class="tiny-btn danger" @click="deleteSubArea(sa.id)">×</button>
        </div>
      </div>

      <div class="divider"></div>

      <!-- Canvas Shortcuts & Help -->
      <div class="shortcuts-card">
        <label>Canvas Guide</label>
        <ul>
          <li><strong>Drag & Drop:</strong> Drag entities from the left panel onto the canvas. Duplicate placements are supported!</li>
          <li><strong>Marquee Box:</strong> Drag on empty canvas space to select multiple entities.</li>
          <li><strong>Shift + Click:</strong> Toggle individual entity selections.</li>
          <li><strong>Group Move:</strong> Drag any selected item to move all selected entities simultaneously.</li>
          <li><strong>Doors & Windows:</strong> Show open vs closed states with swing arc and sash visuals.</li>
        </ul>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.property-panel {
  width: 290px;
  height: calc(100% - 32px);
  margin: 16px;
  display: flex;
  flex-direction: column;
  z-index: 100;
  overflow-y: auto;
  transition: box-shadow 0.2s ease;
}

.property-panel.dock-left {
  order: 1;
}

.property-panel.dock-float {
  position: fixed;
  height: 560px;
  max-height: calc(100vh - 100px);
  z-index: 170;
  box-shadow: 0 16px 40px rgba(0, 0, 0, 0.6), 0 0 0 1px rgba(99, 102, 241, 0.3);
  margin: 0;
}

/* Minimized Floating Pill */
.props-minimized-pill {
  position: fixed;
  z-index: 175;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: var(--radius-full, 24px);
  cursor: grab;
  user-select: none;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary);
  transition: all 0.15s ease;
}

.props-minimized-pill.dock-right {
  right: 20px;
  top: 72px;
}

.props-minimized-pill.dock-left {
  left: 20px;
  top: 72px;
}

.props-minimized-pill:hover {
  transform: translateY(-1px);
  box-shadow: 0 10px 28px rgba(99, 102, 241, 0.3);
  border-color: rgba(99, 102, 241, 0.5);
}

.pill-icon {
  font-size: 14px;
}

.pill-text {
  font-size: 12px;
}

.pill-badge {
  background: var(--accent-primary, #6366f1);
  color: #ffffff;
  padding: 1px 6px;
  border-radius: 10px;
  font-size: 10px;
}

.pill-action-btn {
  background: rgba(255, 255, 255, 0.1);
  border: none;
  color: var(--text-secondary);
  width: 22px;
  height: 22px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  cursor: pointer;
  transition: all 0.12s ease;
}

.pill-action-btn:hover {
  background: var(--accent-primary);
  color: #ffffff;
}

.panel-header {
  padding: 12px 14px 10px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--border-color);
  cursor: grab;
  user-select: none;
}

.panel-header-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}

.panel-tool-btn {
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: var(--text-secondary);
  font-size: 10px;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.12s ease;
}

.panel-tool-btn:hover {
  background: rgba(99, 102, 241, 0.25);
  border-color: #6366f1;
  color: #ffffff;
}

.header-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 8px;
}

.count-badge {
  font-size: 11px;
  padding: 2px 7px;
  background: var(--accent-primary);
  color: #ffffff;
  border-radius: 10px;
  font-weight: 600;
}

.close-btn {
  font-size: 20px;
  line-height: 1;
  color: var(--text-muted);
}

.close-btn:hover {
  color: var(--text-primary);
}

.panel-body {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.tip-card {
  padding: 10px 12px;
  background: rgba(99, 102, 241, 0.12);
  border: 1px solid rgba(99, 102, 241, 0.3);
  border-radius: var(--radius-sm);
  font-size: 12px;
  line-height: 1.4;
  color: #c7d2fe;
}

.prop-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field-help {
  font-size: 11px;
  color: var(--text-muted);
  margin: 0;
}

.prop-row {
  display: flex;
  gap: 10px;
}

.prop-row .prop-group {
  flex: 1;
}

.prop-row-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.rotation-controls {
  display: flex;
  align-items: center;
  gap: 8px;
}

.rotate-slider {
  flex: 1;
}

.rotate-step-btn {
  padding: 4px 6px;
  font-size: 11px;
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  border-radius: var(--radius-sm);
  white-space: nowrap;
}

.rotate-step-btn:hover {
  background: var(--bg-surface-hover);
  color: var(--text-primary);
}

.group-row {
  display: flex;
  gap: 6px;
  align-items: center;
}

.group-row input {
  flex: 1;
}

.tiny-btn {
  padding: 4px 8px;
  font-size: 11px;
  border-radius: var(--radius-sm);
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  cursor: pointer;
}

.tiny-btn.danger {
  background: rgba(239, 68, 68, 0.15);
  border-color: rgba(239, 68, 68, 0.3);
  color: var(--color-danger);
}

.tiny-btn.danger:hover {
  background: rgba(239, 68, 68, 0.25);
}

label {
  font-size: 11px;
  font-weight: 500;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.value-badge {
  font-size: 12px;
  color: var(--text-secondary);
  font-family: var(--font-mono);
}

.readonly-input {
  opacity: 0.7;
  cursor: default;
  font-size: 12px;
  font-family: var(--font-mono);
}

.primary-action-btn {
  padding: 8px 12px;
  background: var(--accent-primary);
  color: #ffffff;
  border-radius: var(--radius-sm);
  font-size: 12px;
  font-weight: 600;
  border: none;
  cursor: pointer;
  transition: background 0.2s ease;
}

.primary-action-btn:hover:not(:disabled) {
  background: var(--accent-primary-hover);
}

.primary-action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.secondary-action-btn {
  padding: 8px 12px;
  background: var(--bg-surface);
  color: var(--text-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
}

.secondary-action-btn:hover {
  background: var(--bg-surface-hover);
}

.divider {
  height: 1px;
  background: var(--border-color);
  margin: 4px 0;
}

.panel-actions {
  margin-top: 8px;
}

.delete-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 8px;
  background: rgba(239, 68, 68, 0.15);
  color: var(--color-danger);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: var(--radius-sm);
  font-size: 13px;
  font-weight: 500;
}

.delete-btn:hover {
  background: rgba(239, 68, 68, 0.25);
}

.subareas-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.subarea-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 10px;
  background: var(--bg-surface);
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-color);
}

.subarea-info {
  display: flex;
  align-items: center;
  gap: 6px;
}

.subarea-name {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-primary);
}

.parent-tag {
  font-size: 10px;
  padding: 1px 5px;
  background: rgba(99, 102, 241, 0.2);
  color: #a5b4fc;
  border-radius: 4px;
}

.shortcuts-card {
  padding: 12px;
  background: var(--bg-surface);
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-color);
}

.shortcuts-card ul {
  margin: 8px 0 0 0;
  padding-left: 18px;
  font-size: 11px;
  line-height: 1.6;
  color: var(--text-secondary);
}

/* Warnings and Alerts */
.attached-badge {
  display: flex;
  align-items: center;
  background: rgba(16, 185, 129, 0.15);
  border: 1px solid rgba(16, 185, 129, 0.3);
  padding: 4px 8px;
  border-radius: 6px;
  gap: 6px;
  margin-top: 4px;
}
.attachment-icon { font-size: 14px; }
.attachment-text { flex: 1; font-size: 13px; color: #a7f3d0; font-weight: 500; }
.remove-attachment-btn {
  background: transparent;
  border: none;
  color: #6ee7b7;
  cursor: pointer;
  font-size: 16px;
  line-height: 1;
  padding: 0 4px;
}
.remove-attachment-btn:hover { color: #fff; }
.warning-alert-box {
  padding: 10px 12px;
  background: rgba(239, 68, 68, 0.12);
  border: 1px solid rgba(239, 68, 68, 0.35);
  border-radius: var(--radius-sm);
  margin-bottom: 12px;
}

.alert-title {
  font-size: 12px;
  font-weight: 600;
  color: #f87171;
  margin-bottom: 4px;
}

.alert-desc {
  font-size: 11px;
  line-height: 1.4;
  color: var(--text-secondary);
  margin: 0;
}

/* Auto-Detect Button */
.auto-detect-btn {
  font-size: 11px;
  font-weight: 500;
  padding: 2px 8px;
  background: rgba(16, 185, 129, 0.15);
  color: #34d399;
  border: 1px solid rgba(16, 185, 129, 0.35);
  border-radius: var(--radius-full);
  cursor: pointer;
  transition: all 0.15s ease;
}

.auto-detect-btn:hover {
  background: rgba(16, 185, 129, 0.25);
  border-color: #34d399;
}

/* Chips List */
.items-chip-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 8px;
}

.chip-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 3px 8px;
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-full);
  font-size: 11px;
  color: var(--text-primary);
}

.chip-item.camera-chip {
  background: rgba(59, 130, 246, 0.12);
  border-color: rgba(59, 130, 246, 0.3);
  color: #93c5fd;
}

.chip-remove {
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  font-size: 13px;
  padding: 0 2px;
  line-height: 1;
}

.chip-remove:hover {
  color: #ef4444;
}

/* Add Item Row */
.add-item-row {
  display: flex;
  gap: 6px;
  align-items: center;
}

.add-item-row select {
  flex: 1;
}

.add-item-btn {
  padding: 6px 12px;
  font-size: 12px;
  font-weight: 500;
  background: var(--accent-primary);
  color: #ffffff;
  border-radius: var(--radius-sm);
  cursor: pointer;
}

.add-item-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Coverage Controls */
.coverage-controls-box {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 10px;
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  margin-top: 6px;
}

.slider-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.slider-info {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: var(--text-secondary);
}

.val-tag {
  color: #818cf8;
  font-weight: 600;
}

.range-slider {
  width: 100%;
}

/* Toggle Switch */
.toggle-switch {
  position: relative;
  display: inline-block;
  width: 32px;
  height: 18px;
}

.toggle-switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.toggle-slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  transition: 0.2s;
  border-radius: 18px;
}

.toggle-slider:before {
  position: absolute;
  content: "";
  height: 12px;
  width: 12px;
  left: 2px;
  bottom: 2px;
  background-color: #94a3b8;
  transition: 0.2s;
  border-radius: 50%;
}

.toggle-switch input:checked + .toggle-slider {
  background-color: var(--accent-primary);
  border-color: var(--accent-primary);
}

.toggle-switch input:checked + .toggle-slider:before {
  transform: translateX(14px);
  background-color: #ffffff;
}
</style>
