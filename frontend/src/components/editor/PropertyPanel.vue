<script setup lang="ts">
import { ref, computed } from "vue";
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
</script>

<template>
  <!-- Multi-Selection Mode -->
  <aside v-if="isMultiSelect" class="property-panel glass-panel">
    <div class="panel-header">
      <div class="header-title">
        <span>Selection</span>
        <span class="count-badge">{{ editorStore.selectedEndpointIds.length }} items</span>
      </div>
      <button class="close-btn" @click="editorStore.clearSelection()">×</button>
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
  <aside v-else-if="selectedEndpoint" class="property-panel glass-panel">
    <div class="panel-header">
      <div class="header-title">Endpoint Properties</div>
      <button class="close-btn" @click="editorStore.clearSelection()">×</button>
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

      <!-- Entity ID (Read-only) -->
      <div class="prop-group">
        <label>Entity ID</label>
        <input type="text" :value="selectedEndpoint.entity_id" readonly class="readonly-input" />
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

  <!-- Default Floor / Sub-Area Management Panel -->
  <aside v-else class="property-panel glass-panel">
    <div class="panel-header">
      <div class="header-title">Floor Areas & Zones</div>
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
}

.panel-header {
  padding: 16px 16px 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--border-color);
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
</style>
