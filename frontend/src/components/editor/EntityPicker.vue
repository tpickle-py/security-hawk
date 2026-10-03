<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import { useEntityStore } from "@/stores/entityStore";
import { usePlanStore } from "@/stores/planStore";
import type { HAEntity } from "@/types/plan";

const entityStore = useEntityStore();
const planStore = usePlanStore();

const query = ref("");
const selectedDomain = ref("");
const activeTab = ref<"all" | "unassigned">("all");
const selectedArea = ref("");
const designatingEntityId = ref<string | null>(null);

const domains = [
  { label: "All", value: "" },
  { label: "Motion", value: "binary_sensor" },
  { label: "Cameras", value: "camera" },
  { label: "Doors", value: "binary_sensor" },
];

const placedEntityCounts = computed(() => {
  const counts = new Map<string, number>();
  for (const ep of planStore.currentEndpoints) {
    counts.set(ep.entity_id, (counts.get(ep.entity_id) || 0) + 1);
  }
  return counts;
});

function handleSearch() {
  entityStore.fetchEntities(
    query.value,
    selectedDomain.value,
    selectedArea.value,
    activeTab.value === "unassigned"
  );
}

function selectDomain(domain: string) {
  selectedDomain.value = domain;
  handleSearch();
}

function selectAreaFilter(e: Event) {
  const target = e.target as HTMLSelectElement;
  selectedArea.value = target.value;
  handleSearch();
}

function toggleUnassignedTab(tab: "all" | "unassigned") {
  activeTab.value = tab;
  handleSearch();
}

async function handleDesignateArea(entityId: string, e: Event) {
  const target = e.target as HTMLSelectElement;
  const newAreaId = target.value || null;
  await entityStore.designateArea(entityId, newAreaId);
  designatingEntityId.value = null;
}

function handleDragStart(e: DragEvent, entity: HAEntity) {
  if (!e.dataTransfer) return;
  const guessedType = entityStore.guessEndpointType(entity);
  const displayName = entity.friendly_name || entity.name || entity.entity_id;
  const payload = {
    entity_id: entity.entity_id,
    device_id: entity.device_id,
    label: displayName,
    type: guessedType,
  };
  e.dataTransfer.setData("application/json", JSON.stringify(payload));
  e.dataTransfer.effectAllowed = "copy";
}

onMounted(async () => {
  await Promise.all([
    entityStore.fetchAreas(),
    entityStore.fetchEntities("", ""),
  ]);
});
</script>

<template>
  <aside class="entity-picker glass-panel">
    <div class="picker-header">
      <div class="header-title">Home Assistant Entities</div>
      <div class="header-subtitle">Drag and drop to place on floor plan</div>
    </div>

    <!-- Quick Tabs: All vs Unassigned Rooms -->
    <div class="unassigned-tab-bar">
      <button
        class="tab-btn"
        :class="{ active: activeTab === 'all' }"
        @click="toggleUnassignedTab('all')"
      >
        All Entities
      </button>
      <button
        class="tab-btn unassigned-btn"
        :class="{ active: activeTab === 'unassigned' }"
        @click="toggleUnassignedTab('unassigned')"
      >
        <span>Unassigned</span>
        <span class="count-pill" v-if="entityStore.unassignedCount > 0">
          {{ entityStore.unassignedCount }}
        </span>
      </button>
    </div>

    <!-- Search Input (friendly name, id, or room) -->
    <div class="search-box">
      <svg class="search-icon" viewBox="0 0 24 24" width="16" height="16">
        <path fill="currentColor" d="M9.5,3A6.5,6.5 0 0,1 16,9.5C16,11.11 15.41,12.59 14.44,13.73L14.71,14H15.5L20.5,19L19,20.5L14,15.5V14.71L13.73,14.44C12.59,15.41 11.11,16 9.5,16A6.5,6.5 0 0,1 3,9.5A6.5,6.5 0 0,1 9.5,3M9.5,5C7,5 5,7 5,9.5C5,12 7,14 9.5,14C12,14 14,12 14,9.5C14,7 12,5 9.5,5Z"/>
      </svg>
      <input
        type="text"
        v-model="query"
        placeholder="Search by friendly name, room..."
        @input="handleSearch"
      />
    </div>

    <!-- Filter Row: Domains & Area Dropdown -->
    <div class="filter-controls">
      <div class="domain-filters">
        <button
          v-for="d in domains"
          :key="d.label"
          class="filter-chip"
          :class="{ active: selectedDomain === d.value }"
          @click="selectDomain(d.value)"
        >
          {{ d.label }}
        </button>
      </div>

      <div class="area-select-wrapper" v-if="entityStore.areas.length > 0">
        <select :value="selectedArea" @change="selectAreaFilter" class="area-dropdown">
          <option value="">All Rooms / Areas</option>
          <option v-for="a in entityStore.areas" :key="a.area_id" :value="a.area_id">
            {{ a.name }}
          </option>
        </select>
      </div>
    </div>

    <!-- Entity List -->
    <div class="entity-list">
      <div v-if="entityStore.isLoading" class="list-state">Loading entities...</div>
      <div v-else-if="entityStore.entities.length === 0" class="list-state">
        <span v-if="activeTab === 'unassigned'">All entities have been assigned to rooms! 🎉</span>
        <span v-else>No matching entities found.</span>
      </div>

      <div
        v-for="ent in entityStore.entities"
        :key="ent.entity_id"
        class="entity-item"
        :class="{ placed: (placedEntityCounts.get(ent.entity_id) || 0) > 0 }"
        draggable="true"
        @dragstart="handleDragStart($event, ent)"
      >
        <div class="entity-icon-badge" :class="entityStore.guessEndpointType(ent)">
          <span v-if="entityStore.guessEndpointType(ent) === 'motion'">🏃</span>
          <span v-else-if="entityStore.guessEndpointType(ent) === 'door'">🚪</span>
          <span v-else-if="entityStore.guessEndpointType(ent) === 'camera'">📹</span>
          <span v-else>📡</span>
        </div>

        <div class="entity-details">
          <!-- Friendly Name Prominently -->
          <div class="entity-name" :title="ent.friendly_name || ent.name || ent.entity_id">
            {{ ent.friendly_name || ent.name || ent.entity_id }}
          </div>

          <div class="entity-sub">
            <span class="entity-id" :title="ent.entity_id">{{ ent.entity_id }}</span>
          </div>

          <!-- Room / Area Designation Bar -->
          <div class="area-designation-row">
            <template v-if="designatingEntityId === ent.entity_id">
              <select
                class="designate-select"
                :value="ent.area_id || ''"
                @change="handleDesignateArea(ent.entity_id, $event)"
                @blur="designatingEntityId = null"
                autofocus
              >
                <option value="">-- No Area / Unassigned --</option>
                <option v-for="a in entityStore.areas" :key="a.area_id" :value="a.area_id">
                  {{ a.name }}
                </option>
              </select>
            </template>
            <template v-else>
              <button
                v-if="ent.area_name"
                class="area-tag"
                title="Click to reassign room/area"
                @click.stop="designatingEntityId = ent.entity_id"
              >
                📍 {{ ent.area_name }}
              </button>
              <button
                v-else
                class="assign-area-btn"
                title="Designate room/area"
                @click.stop="designatingEntityId = ent.entity_id"
              >
                + Assign Room
              </button>
            </template>
          </div>
        </div>

        <div
          v-if="(placedEntityCounts.get(ent.entity_id) || 0) > 0"
          class="placed-badge"
          :title="`Placed ${placedEntityCounts.get(ent.entity_id)} time(s) on floor. Drag to place another duplicate instance.`"
        >
          <span v-if="(placedEntityCounts.get(ent.entity_id) || 0) === 1">Placed</span>
          <span v-else>Placed ×{{ placedEntityCounts.get(ent.entity_id) }}</span>
        </div>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.entity-picker {
  width: 320px;
  height: calc(100% - 32px);
  margin: 16px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  z-index: 100;
}

.picker-header {
  padding: 14px 16px 8px;
}

.header-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.header-subtitle {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 2px;
}

.unassigned-tab-bar {
  display: flex;
  margin: 0 16px 10px;
  background: var(--bg-surface);
  padding: 3px;
  border-radius: var(--radius-sm);
  gap: 4px;
}

.tab-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 5px 8px;
  font-size: 11px;
  font-weight: 500;
  color: var(--text-secondary);
  border-radius: var(--radius-sm);
}

.tab-btn.active {
  background: var(--accent-primary);
  color: #ffffff;
}

.count-pill {
  background: var(--color-warning);
  color: #1e293b;
  font-size: 10px;
  font-weight: 700;
  padding: 1px 5px;
  border-radius: var(--radius-full);
}

.search-box {
  position: relative;
  margin: 0 16px 10px;
}

.search-icon {
  position: absolute;
  left: 10px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--text-muted);
  pointer-events: none;
}

.search-box input {
  width: 100%;
  padding-left: 32px;
  font-size: 12px;
  background-color: rgba(15, 23, 42, 0.6);
}

.filter-controls {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 0 16px 10px;
}

.domain-filters {
  display: flex;
  gap: 4px;
  overflow-x: auto;
}

.filter-chip {
  padding: 3px 8px;
  font-size: 11px;
  font-weight: 500;
  color: var(--text-secondary);
  background: var(--bg-surface);
  border-radius: var(--radius-full);
  white-space: nowrap;
}

.filter-chip.active {
  background: var(--accent-primary);
  color: #ffffff;
}

.area-dropdown {
  width: 100%;
  font-size: 11px;
  padding: 4px 8px;
  background-color: var(--bg-surface);
}

.entity-list {
  flex: 1;
  overflow-y: auto;
  padding: 0 8px 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.list-state {
  text-align: center;
  padding: 24px 16px;
  color: var(--text-muted);
  font-size: 12px;
}

.entity-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px;
  background: rgba(30, 41, 59, 0.6);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  cursor: grab;
  transition: all 0.15s ease;
}

.entity-item:hover {
  background: rgba(51, 65, 85, 0.8);
  border-color: rgba(99, 102, 241, 0.4);
  transform: translateY(-1px);
}

.entity-item:active {
  cursor: grabbing;
}

.entity-item.placed {
  border-color: rgba(99, 102, 241, 0.3);
  background: rgba(30, 41, 59, 0.85);
}

.entity-icon-badge {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 15px;
  background: var(--bg-surface);
  flex-shrink: 0;
  margin-top: 2px;
}

.entity-icon-badge.motion {
  background: rgba(239, 68, 68, 0.15);
}

.entity-icon-badge.door {
  background: rgba(245, 158, 11, 0.15);
}

.entity-icon-badge.camera {
  background: rgba(99, 102, 241, 0.15);
}

.entity-details {
  flex: 1;
  min-width: 0;
}

.entity-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.entity-sub {
  font-size: 11px;
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-top: 1px;
}

.area-designation-row {
  margin-top: 5px;
}

.area-tag {
  font-size: 10px;
  color: var(--text-secondary);
  background: rgba(99, 102, 241, 0.15);
  border: 1px solid rgba(99, 102, 241, 0.3);
  padding: 1px 6px;
  border-radius: var(--radius-sm);
}

.area-tag:hover {
  color: #ffffff;
  background: rgba(99, 102, 241, 0.3);
}

.assign-area-btn {
  font-size: 10px;
  color: var(--color-warning);
  background: rgba(245, 158, 11, 0.1);
  border: 1px dashed rgba(245, 158, 11, 0.4);
  padding: 1px 6px;
  border-radius: var(--radius-sm);
}

.assign-area-btn:hover {
  background: rgba(245, 158, 11, 0.2);
}

.designate-select {
  font-size: 10px;
  padding: 2px 4px;
  width: 100%;
}

.placed-badge {
  font-size: 10px;
  font-weight: 500;
  background: rgba(16, 185, 129, 0.15);
  color: var(--color-success);
  padding: 2px 6px;
  border-radius: var(--radius-full);
  margin-top: 2px;
}
</style>
