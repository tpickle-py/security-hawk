<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import { useEntityStore } from "@/stores/entityStore";
import { usePlanStore } from "@/stores/planStore";
import type { CompositeRule, HAEntity } from "@/types/plan";
import { api } from "@/services/api";
import RuleBuilderModal from "@/components/editor/RuleBuilderModal.vue";

const entityStore = useEntityStore();
const planStore = usePlanStore();

const query = ref("");
const selectedDomain = ref("");
const activeTab = ref<"all" | "unassigned" | "rules">("all");
const selectedArea = ref("");
const designatingEntityId = ref<string | null>(null);

// Rules state
const rules = ref<CompositeRule[]>([]);
const isLoadingRules = ref(false);
const showRuleBuilder = ref(false);
const ruleToEdit = ref<CompositeRule | null>(null);

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
  if (activeTab.value === "rules") {
    // search filter handled in-memory for rules
    return;
  }
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

async function fetchRules() {
  try {
    isLoadingRules.value = true;
    const res = await api.getRules();
    rules.value = res.rules;
  } catch (e) {
    console.error("Failed to load rules", e);
  } finally {
    isLoadingRules.value = false;
  }
}

function switchTab(tab: "all" | "unassigned" | "rules") {
  activeTab.value = tab;
  if (tab === "rules") {
    fetchRules();
  } else {
    handleSearch();
  }
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

function handleRuleDragStart(e: DragEvent, rule: CompositeRule) {
  if (!e.dataTransfer) return;
  const targetEntityId = rule.output_entity_id || `binary_sensor.security_hawk_${rule.id}`;
  const payload = {
    entity_id: targetEntityId,
    device_id: null,
    label: rule.name,
    type: "composite",
  };
  e.dataTransfer.setData("application/json", JSON.stringify(payload));
  e.dataTransfer.effectAllowed = "copy";
}

function openCreateRule() {
  ruleToEdit.value = null;
  showRuleBuilder.value = true;
}

function openEditRule(rule: CompositeRule) {
  ruleToEdit.value = rule;
  showRuleBuilder.value = true;
}

async function deleteRule(ruleId: string) {
  if (!confirm("Are you sure you want to delete this compound rule?")) return;
  try {
    await api.deleteRule(ruleId);
    await fetchRules();
  } catch (err: any) {
    alert(err.message || "Failed to delete rule");
  }
}

const filteredRules = computed(() => {
  if (!query.value.trim()) return rules.value;
  const q = query.value.toLowerCase();
  return rules.value.filter(
    (r) =>
      r.name.toLowerCase().includes(q) ||
      (r.output_entity_id && r.output_entity_id.toLowerCase().includes(q))
  );
});

onMounted(async () => {
  await Promise.all([
    entityStore.fetchAreas(),
    entityStore.fetchEntities("", ""),
    fetchRules(),
  ]);
});
</script>

<template>
  <aside class="entity-picker glass-panel">
    <div class="picker-header">
      <div class="header-title">Home Assistant Entities</div>
      <div class="header-subtitle">Drag and drop to place on floor plan</div>
    </div>

    <!-- Quick Tabs: All vs Unassigned Rooms vs Rules -->
    <div class="unassigned-tab-bar">
      <button
        class="tab-btn"
        :class="{ active: activeTab === 'all' }"
        @click="switchTab('all')"
      >
        All
      </button>
      <button
        class="tab-btn unassigned-btn"
        :class="{ active: activeTab === 'unassigned' }"
        @click="switchTab('unassigned')"
      >
        <span>Unassigned</span>
        <span class="count-pill" v-if="entityStore.unassignedCount > 0">
          {{ entityStore.unassignedCount }}
        </span>
      </button>
      <button
        class="tab-btn rules-tab-btn"
        :class="{ active: activeTab === 'rules' }"
        @click="switchTab('rules')"
      >
        <span>⚡ Rules</span>
        <span class="count-pill rules-pill" v-if="rules.length > 0">
          {{ rules.length }}
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
        :placeholder="activeTab === 'rules' ? 'Search rules...' : 'Search by friendly name, room...'"
        @input="handleSearch"
      />
    </div>

    <!-- Filter Row: Domains & Area Dropdown (when not in rules tab) -->
    <div class="filter-controls" v-if="activeTab !== 'rules'">
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

    <!-- Rules Action Bar (when in rules tab) -->
    <div class="rules-action-bar" v-else>
      <button class="btn-create-rule" @click="openCreateRule">
        <span>+</span> New Compound Rule
      </button>
    </div>

    <!-- RULES VIEW -->
    <div v-if="activeTab === 'rules'" class="entity-list">
      <div v-if="isLoadingRules" class="list-state">Loading compound rules...</div>
      <div v-else-if="filteredRules.length === 0" class="list-state">
        <p>No compound rules created yet.</p>
        <button class="btn-create-rule-empty" @click="openCreateRule">
          Create Your First Rule
        </button>
      </div>

      <div
        v-for="rule in filteredRules"
        :key="rule.id"
        class="entity-item rule-item"
        :class="{ placed: (placedEntityCounts.get(rule.output_entity_id || `binary_sensor.security_hawk_${rule.id}`) || 0) > 0 }"
        draggable="true"
        @dragstart="handleRuleDragStart($event, rule)"
      >
        <div class="entity-icon-badge rule-icon-badge">
          <span>⚡</span>
        </div>

        <div class="entity-details">
          <div class="entity-name" :title="rule.name">
            {{ rule.name }}
          </div>

          <div class="entity-sub">
            <span class="entity-id">{{ rule.output_entity_id || `binary_sensor.security_hawk_${rule.id}` }}</span>
          </div>

          <div class="rule-meta-row">
            <span class="rule-cond-pill">
              {{ rule.conditions?.length || 0 }} cond ({{ rule.logic }})
            </span>
            <span class="rule-cond-pill">
              ⏱️ {{ rule.time_window_seconds }}s
            </span>
            <span v-if="rule.linked_cameras && rule.linked_cameras.length > 0" class="rule-cond-pill cam">
              📹 {{ rule.linked_cameras.length }} cam
            </span>
          </div>

          <div class="rule-actions-row">
            <button class="rule-action-btn edit" @click.stop="openEditRule(rule)">
              Edit
            </button>
            <button class="rule-action-btn del" @click.stop="deleteRule(rule.id)">
              Delete
            </button>
          </div>
        </div>

        <div
          v-if="(placedEntityCounts.get(rule.output_entity_id || `binary_sensor.security_hawk_${rule.id}`) || 0) > 0"
          class="placed-badge"
          title="Placed on floor plan"
        >
          Placed
        </div>
      </div>
    </div>

    <!-- ENTITY LIST (HA Physical Entities) -->
    <div v-else class="entity-list">
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

    <!-- Rule Builder Modal Component -->
    <RuleBuilderModal
      :show="showRuleBuilder"
      :ruleToEdit="ruleToEdit"
      @close="showRuleBuilder = false"
      @saved="fetchRules"
    />
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

.rules-pill {
  background: var(--accent-primary);
  color: #ffffff;
}

.rules-action-bar {
  padding: 0 16px 10px;
}

.btn-create-rule {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  background: rgba(139, 92, 246, 0.2);
  border: 1px dashed #8b5cf6;
  color: #c4b5fd;
  padding: 7px 12px;
  border-radius: var(--radius-sm);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-create-rule:hover {
  background: rgba(139, 92, 246, 0.35);
  color: #ffffff;
}

.btn-create-rule-empty {
  margin-top: 10px;
  background: var(--accent-primary);
  color: #ffffff;
  border: none;
  padding: 6px 14px;
  border-radius: var(--radius-sm);
  font-size: 12px;
  cursor: pointer;
}

.rule-item {
  border-left: 3px solid #8b5cf6;
}

.rule-icon-badge {
  background: rgba(139, 92, 246, 0.2);
  color: #c4b5fd;
}

.rule-meta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 6px;
}

.rule-cond-pill {
  font-size: 10px;
  background: rgba(15, 23, 42, 0.7);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: var(--text-secondary);
  padding: 1px 5px;
  border-radius: var(--radius-sm);
}

.rule-cond-pill.cam {
  color: #818cf8;
  border-color: rgba(129, 140, 248, 0.3);
}

.rule-actions-row {
  display: flex;
  gap: 6px;
  margin-top: 6px;
}

.rule-action-btn {
  font-size: 10px;
  font-weight: 500;
  padding: 2px 7px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
}

.rule-action-btn:hover {
  background: rgba(255, 255, 255, 0.15);
  color: #ffffff;
}

.rule-action-btn.del:hover {
  background: rgba(239, 68, 68, 0.2);
  color: #fca5a5;
  border-color: rgba(239, 68, 68, 0.4);
}
</style>
