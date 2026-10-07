<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from "vue";
import { useEntityStore } from "@/stores/entityStore";
import { usePlanStore } from "@/stores/planStore";
import type { CompositeRule, HAEntity } from "@/types/plan";
import { api } from "@/services/api";
import RuleBuilderModal from "@/components/editor/RuleBuilderModal.vue";
import SmartMatchModal from "@/components/editor/SmartMatchModal.vue";
import { findSmartMatches } from "@/services/keywordMatcher";

const entityStore = useEntityStore();
const planStore = usePlanStore();

const showSmartMatchModal = ref(false);

const query = ref("");
const selectedDomain = ref("");
const activeTab = ref<"all" | "unassigned" | "rules" | "ignored">("all");
const selectedArea = ref("");
const designatingEntityId = ref<string | null>(null);

// Bulk hide state
const showBulkHideModal = ref(false);
const domainSearchQuery = ref("");
const quickDomains = ["switch", "light", "automation", "scene", "script", "update", "sensor"];
const nonSecurityPresetDomains = [
  "switch",
  "light",
  "automation",
  "scene",
  "script",
  "update",
  "input_boolean",
  "timer",
  "counter",
];

// Rules state
const rules = ref<CompositeRule[]>([]);
const isLoadingRules = ref(false);
const showRuleBuilder = ref(false);
const ruleToEdit = ref<CompositeRule | null>(null);

const domains = [
  { label: "All", value: "" },
  { label: "Cameras", value: "camera" },
  { label: "Motion", value: "motion" },
  { label: "Doors", value: "door" },
  { label: "Windows", value: "window" },
];

const selectedDomainLabel = computed(() => {
  const d = domains.find((item) => item.value === selectedDomain.value);
  return d && d.value ? d.label : "";
});

const selectedAreaName = computed(() => {
  if (!selectedArea.value) return "";
  const a = entityStore.areas.find((item) => item.area_id === selectedArea.value);
  return a ? a.name : "";
});

// Domain and Area aware Smart Match computation
const smartMatches = computed(() => {
  let candidates = entityStore.unassignedEntities;

  if (selectedDomain.value) {
    candidates = candidates.filter((e) => {
      const gType = entityStore.guessEndpointType(e);
      if (selectedDomain.value === "camera") return e.domain === "camera" || gType === "camera";
      if (selectedDomain.value === "motion") return gType === "motion";
      if (selectedDomain.value === "door") return gType === "door";
      if (selectedDomain.value === "window") return gType === "window";
      return e.domain === selectedDomain.value;
    });
  }

  let targetAreas = entityStore.areas;
  if (selectedArea.value) {
    targetAreas = targetAreas.filter((a) => a.area_id === selectedArea.value);
  }

  return findSmartMatches(candidates, targetAreas);
});

// Filtered entities to display in list
const displayEntities = computed(() => {
  if (activeTab.value === "all") {
    return entityStore.visibleEntities;
  }
  if (activeTab.value === "unassigned") {
    let list = entityStore.unassignedEntities;
    if (selectedDomain.value) {
      list = list.filter((e) => {
        const gType = entityStore.guessEndpointType(e);
        if (selectedDomain.value === "camera") return e.domain === "camera" || gType === "camera";
        if (selectedDomain.value === "motion") return gType === "motion";
        if (selectedDomain.value === "door") return gType === "door";
        if (selectedDomain.value === "window") return gType === "window";
        return e.domain === selectedDomain.value;
      });
    }
    if (selectedArea.value) {
      const matchMap = new Set(smartMatches.value.map((m) => m.entity.entity_id));
      list = list.filter((e) => matchMap.has(e.entity_id));
    }
    return list;
  }
  return [];
});

const placedEntityCounts = computed(() => {
  const counts = new Map<string, number>();
  for (const ep of planStore.currentEndpoints) {
    counts.set(ep.entity_id, (counts.get(ep.entity_id) || 0) + 1);
  }
  return counts;
});

function handleSearch() {
  if (activeTab.value === "rules") {
    return;
  }
  const queryAreaId = activeTab.value === "unassigned" ? "" : selectedArea.value;
  entityStore.fetchEntities(
    query.value,
    selectedDomain.value,
    queryAreaId,
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

function switchTab(tab: "all" | "unassigned" | "rules" | "ignored") {
  activeTab.value = tab;
  if (tab === "rules") {
    fetchRules();
  } else if (tab === "ignored") {
    // rendered from ignoredEntitiesList & ignoredDomains
  } else {
    handleSearch();
  }
}

const ignoredEntitiesList = computed(() => {
  const q = query.value.toLowerCase().trim();
  return entityStore.ignoredEntityIds
    .map((eid) => {
      const ent = entityStore.entities.find((e) => e.entity_id === eid);
      return {
        entity_id: eid,
        friendly_name: ent?.friendly_name || ent?.name || eid,
        area_name: ent?.area_name,
        type: ent ? entityStore.guessEndpointType(ent) : "generic",
      };
    })
    .filter(
      (e) =>
        !q ||
        e.entity_id.toLowerCase().includes(q) ||
        e.friendly_name.toLowerCase().includes(q)
    );
});

function getDomainIcon(domain: string): string {
  switch (domain) {
    case "switch":
      return "🔌";
    case "light":
      return "💡";
    case "automation":
      return "⚙️";
    case "script":
      return "📜";
    case "scene":
      return "🎬";
    case "update":
      return "🔄";
    case "sensor":
      return "🌡️";
    case "binary_sensor":
      return "🏃";
    case "camera":
      return "📹";
    case "lock":
      return "🔒";
    case "siren":
      return "🚨";
    case "alarm_control_panel":
      return "🛡️";
    case "cover":
      return "🪟";
    case "climate":
      return "❄️";
    case "media_player":
      return "🔊";
    case "person":
      return "👤";
    case "device_tracker":
      return "📍";
    case "input_boolean":
      return "🔘";
    case "button":
      return "🔘";
    case "weather":
      return "⛅";
    default:
      return "📦";
  }
}

function isSecurityDomain(domain: string): boolean {
  return ["camera", "binary_sensor", "lock", "alarm_control_panel", "siren"].includes(domain);
}

const filteredDetectedDomains = computed(() => {
  const q = domainSearchQuery.value.toLowerCase().trim();
  if (!q) return entityStore.detectedDomains;
  return entityStore.detectedDomains.filter((d) => d.domain.toLowerCase().includes(q));
});

async function toggleDomainIgnore(domain: string) {
  await entityStore.toggleIgnoreDomain(domain);
  handleSearch();
}

async function hideNonSecurityPreset() {
  await entityStore.ignoreMultipleDomains(nonSecurityPresetDomains);
  handleSearch();
}

async function restoreAllDomains() {
  await entityStore.unignoreAllDomains();
  handleSearch();
}

async function restoreAllIgnored() {
  await entityStore.unignoreAll();
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

// Docking, minimize, and free move state
export type EntityDockMode = "left" | "right" | "float";
const dockMode = ref<EntityDockMode>(getInitialEntityDock());
const isMinimized = ref<boolean>(localStorage.getItem("sh_entities_min") === "true");
const floatPos = ref<{ x: number; y: number }>(getInitialEntityPos());
const isDraggingHeader = ref(false);

function getInitialEntityDock(): EntityDockMode {
  try {
    const saved = localStorage.getItem("sh_entities_dock");
    if (saved && ["left", "right", "float"].includes(saved)) {
      return saved as EntityDockMode;
    }
  } catch {}
  return "left";
}

function getInitialEntityPos(): { x: number; y: number } {
  try {
    const saved = localStorage.getItem("sh_entities_pos");
    if (saved) {
      const parsed = JSON.parse(saved);
      if (typeof parsed.x === "number" && typeof parsed.y === "number") {
        return parsed;
      }
    }
  } catch {}
  return { x: 24, y: 72 };
}

function setDockMode(mode: EntityDockMode) {
  dockMode.value = mode;
  try {
    localStorage.setItem("sh_entities_dock", mode);
  } catch {}
}

function cycleDockMode() {
  const modes: EntityDockMode[] = ["left", "right", "float"];
  const next = modes[(modes.indexOf(dockMode.value) + 1) % modes.length];
  setDockMode(next);
}

function toggleMinimize() {
  isMinimized.value = !isMinimized.value;
  try {
    localStorage.setItem("sh_entities_min", String(isMinimized.value));
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
        origX = Math.max(10, Math.min(window.innerWidth - 340, startClientX - 160));
        origY = Math.max(10, Math.min(window.innerHeight - 100, startClientY - 20));
      }
    }
    if (hasMoved || origDockMode === "float") {
      floatPos.value = {
        x: Math.max(10, Math.min(window.innerWidth - 330, origX + dx)),
        y: Math.max(10, Math.min(window.innerHeight - 80, origY + dy)),
      };
    }
  };

  const onMouseUp = () => {
    isDraggingHeader.value = false;
    window.removeEventListener("mousemove", onMouseMove);
    window.removeEventListener("mouseup", onMouseUp);
    try {
      localStorage.setItem("sh_entities_pos", JSON.stringify(floatPos.value));
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
    setDockMode("left");
  }
}

onMounted(async () => {
  window.addEventListener("sh-workspace-preset", onWorkspacePreset);
  await Promise.all([
    entityStore.loadSettingsIgnored(),
    entityStore.fetchKnownEntityIds(),
    entityStore.fetchAreas(),
    entityStore.fetchEntities("", ""),
    fetchRules(),
  ]);
});

onUnmounted(() => {
  window.removeEventListener("sh-workspace-preset", onWorkspacePreset);
});
</script>

<template>
  <!-- Minimized Floating Pill -->
  <div
    v-if="isMinimized"
    :class="['entity-minimized-pill', 'glass-panel', `dock-${dockMode}`]"
    :style="dockMode === 'float' ? { left: `${floatPos.x}px`, top: `${floatPos.y}px` } : undefined"
    @mousedown="startHeaderDrag($event)"
    @click="toggleMinimize"
    title="Click to restore Home Assistant Entities panel (drag to move)"
  >
    <span class="pill-icon">🏷️</span>
    <span class="pill-text">Entities</span>
    <span class="pill-badge" v-if="entityStore.unassignedCount > 0">{{ entityStore.unassignedCount }}</span>
    <button class="pill-action-btn" @click.stop="cycleDockMode" :title="`Docked: ${dockMode.toUpperCase()}. Click to cycle.`">
      ⚓
    </button>
    <button class="pill-action-btn" @click.stop="toggleMinimize" title="Expand panel">
      ▲
    </button>
  </div>

  <!-- Expanded Entities Panel -->
  <aside
    v-else
    :class="['entity-picker', 'glass-panel', `dock-${dockMode}`]"
    :style="dockMode === 'float' ? { left: `${floatPos.x}px`, top: `${floatPos.y}px` } : undefined"
  >
    <div class="picker-header" @mousedown="startHeaderDrag">
      <div class="header-info">
        <div class="header-title">Home Assistant Entities</div>
        <div class="header-subtitle">Drag and drop to place on floor plan</div>
      </div>
      <div class="panel-header-actions" @mousedown.stop>
        <button
          class="panel-tool-btn"
          :title="`Dock: ${dockMode.toUpperCase()}. Click to cycle (Left, Right, Float)`"
          @click="cycleDockMode"
        >
          ⚓ {{ dockMode.toUpperCase() }}
        </button>
        <button
          class="panel-tool-btn"
          title="Minimize panel into floating pill"
          @click="toggleMinimize"
        >
          ─
        </button>
      </div>
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
      <button
        class="tab-btn hidden-tab-btn"
        :class="{ active: activeTab === 'ignored' }"
        @click="switchTab('ignored')"
        title="View hidden/ignored entities and domains"
      >
        <span>Hidden</span>
        <span
          class="count-pill ignored-pill"
          v-if="(entityStore.ignoredEntityIds.length + entityStore.ignoredDomains.length) > 0"
        >
          {{ entityStore.ignoredEntityIds.length + entityStore.ignoredDomains.length }}
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
        <button
          class="filter-chip bulk-hide-chip"
          :class="{ 'has-hidden': entityStore.ignoredDomains.length > 0 }"
          @click="showBulkHideModal = true"
          title="Bulk hide entire entity types (switch, light, automation, etc.)"
        >
          <span>🚫 Bulk Hide</span>
          <span class="chip-badge" v-if="entityStore.ignoredDomains.length > 0">
            {{ entityStore.ignoredDomains.length }}
          </span>
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

    <!-- IGNORED / HIDDEN ENTITIES & DOMAINS VIEW -->
    <div v-else-if="activeTab === 'ignored'" class="entity-list ignored-view-list">
      <!-- Quick Domain Management Panel -->
      <div class="bulk-hide-panel">
        <div class="bulk-panel-header">
          <span class="bulk-panel-title">🚫 Bulk Hide Types</span>
          <button
            class="btn-open-bulk-modal"
            @click="showBulkHideModal = true"
            title="Open Full Domain Filter Modal"
          >
            All Types ({{ entityStore.detectedDomains.length }})
          </button>
        </div>

        <div class="bulk-quick-pills">
          <button
            v-for="d in quickDomains"
            :key="d"
            class="domain-toggle-pill"
            :class="{ hidden: entityStore.isDomainIgnored(d) }"
            @click="toggleDomainIgnore(d)"
            :title="entityStore.isDomainIgnored(d) ? `Click to unhide all ${d} entities` : `Click to hide all ${d} entities`"
          >
            <span class="pill-icon">{{ getDomainIcon(d) }}</span>
            <span class="pill-label">{{ d }}</span>
            <span class="pill-status">{{ entityStore.isDomainIgnored(d) ? 'Hidden' : '+' }}</span>
          </button>
        </div>

        <!-- Active Hidden Domains Tags -->
        <div v-if="entityStore.ignoredDomains.length > 0" class="active-hidden-domains">
          <div class="active-domains-header">
            <span>Hidden Categories ({{ entityStore.ignoredDomains.length }}):</span>
            <button class="btn-text-action" @click="restoreAllDomains">Restore All Types</button>
          </div>
          <div class="hidden-domain-tags">
            <span
              v-for="d in entityStore.ignoredDomains"
              :key="d"
              class="hidden-tag"
            >
              <span class="tag-icon">{{ getDomainIcon(d) }}</span>
              <span class="tag-name">{{ d }}</span>
              <button
                class="tag-close-btn"
                @click="toggleDomainIgnore(d)"
                :title="`Unhide ${d}`"
              >✕</button>
            </span>
          </div>
        </div>
      </div>

      <!-- Specific Hidden Devices Section -->
      <div class="hidden-entities-section">
        <div class="hidden-section-header">
          <span class="hidden-title">
            Specifically Hidden Devices
            <span v-if="ignoredEntitiesList.length > 0">({{ ignoredEntitiesList.length }})</span>
          </span>
          <button
            v-if="entityStore.ignoredEntityIds.length > 0"
            class="btn-text-action danger"
            @click="restoreAllIgnored"
            title="Unhide all entities and categories"
          >
            Reset All
          </button>
        </div>

        <div v-if="ignoredEntitiesList.length === 0" class="list-state empty-hidden">
          <p v-if="entityStore.ignoredDomains.length === 0">No hidden devices or categories.</p>
          <span class="hint-text" v-if="entityStore.ignoredDomains.length === 0">
            Click the "Hide" button on any device or use Bulk Hide above to keep your floor plan uncluttered.
          </span>
          <span class="hint-text" v-else>
            No individual devices hidden. {{ entityStore.ignoredDomains.length }} category(ies) are currently bulk-hidden.
          </span>
        </div>

        <div
          v-for="ent in ignoredEntitiesList"
          :key="ent.entity_id"
          class="entity-item ignored-item"
        >
          <div class="entity-icon-badge" :class="ent.type">
            <span v-if="ent.type === 'motion'">🏃</span>
            <span v-else-if="ent.type === 'door'">🚪</span>
            <span v-else-if="ent.type === 'window'">🪟</span>
            <span v-else-if="ent.type === 'camera'">📹</span>
            <span v-else>📡</span>
          </div>
          <div class="entity-details">
            <div class="entity-name" :title="ent.friendly_name">
              {{ ent.friendly_name }}
            </div>
            <div class="entity-sub">
              <span class="entity-id" :title="ent.entity_id">{{ ent.entity_id }}</span>
            </div>
            <div v-if="ent.area_name" class="area-designation-row">
              <span class="area-tag">📍 {{ ent.area_name }}</span>
            </div>
          </div>
          <button
            class="btn-unhide-entity"
            title="Unhide / Restore this entity to Security Hawk"
            @click.stop="entityStore.unignoreEntity(ent.entity_id)"
          >
            👁️ Restore
          </button>
        </div>
      </div>
    </div>

    <!-- UNASSIGNED OR ALL PHYSICAL ENTITIES VIEW -->
    <template v-else-if="activeTab === 'all' || activeTab === 'unassigned'">
      <!-- Smart Match Action Banner (Unassigned Tab) -->
      <div
        v-if="activeTab === 'unassigned' && smartMatches.length > 0"
        class="smart-match-banner"
      >
        <div class="banner-text">
          <span class="banner-sparkle">🪄</span>
          <div class="banner-details">
            <span class="banner-title">Smart Match Found</span>
            <span class="banner-sub">
              {{ smartMatches.length }} unassigned {{ selectedDomainLabel ? selectedDomainLabel : 'entit' + (smartMatches.length === 1 ? 'y' : 'ies') }}
              <template v-if="selectedAreaName"> matching {{ selectedAreaName }}</template>
              <template v-else> match room names</template>
            </span>
          </div>
        </div>
        <button
          class="btn-smart-match"
          @click="showSmartMatchModal = true"
          title="Review and batch-assign matching rooms"
        >
          Auto-Assign
        </button>
      </div>

      <!-- ENTITY LIST (HA Physical Entities) -->
      <div class="entity-list">
        <div v-if="entityStore.isLoading" class="list-state">Loading entities...</div>
        <div v-else-if="displayEntities.length === 0" class="list-state">
          <span v-if="activeTab === 'unassigned' && selectedAreaName">
            No unassigned {{ selectedDomainLabel || 'entities' }} matching {{ selectedAreaName }}.
          </span>
          <span v-else-if="activeTab === 'unassigned'">
            All entities have been assigned to rooms! 🎉
          </span>
          <span v-else>No matching entities found.</span>
        </div>

        <div
          v-for="ent in displayEntities"
          :key="ent.entity_id"
          class="entity-item"
          :class="{ placed: (placedEntityCounts.get(ent.entity_id) || 0) > 0 }"
          draggable="true"
          @dragstart="handleDragStart($event, ent)"
        >
        <div class="entity-icon-badge" :class="entityStore.guessEndpointType(ent)">
          <span v-if="entityStore.guessEndpointType(ent) === 'motion'">🏃</span>
          <span v-else-if="entityStore.guessEndpointType(ent) === 'door'">🚪</span>
          <span v-else-if="entityStore.guessEndpointType(ent) === 'window'">🪟</span>
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

        <div class="entity-actions-col">
          <div
            v-if="(placedEntityCounts.get(ent.entity_id) || 0) > 0"
            class="placed-badge"
            :title="`Placed ${placedEntityCounts.get(ent.entity_id)} time(s) on floor.`"
          >
            <span v-if="(placedEntityCounts.get(ent.entity_id) || 0) === 1">Placed</span>
            <span v-else>Placed ×{{ placedEntityCounts.get(ent.entity_id) }}</span>
          </div>
          <button
            class="btn-hide-entity"
            title="Hide / Ignore this entity"
            @click.stop="entityStore.ignoreEntity(ent.entity_id)"
          >
            <svg viewBox="0 0 24 24" width="13" height="13">
              <path fill="currentColor" d="M11.83,9L15,12.16C15,12.11 15,12.05 15,12A3,3 0 0,0 12,9C11.94,9 11.89,9 11.83,9M7.53,9.8L9.08,11.35C9.03,11.56 9,11.77 9,12A3,3 0 0,0 12,15C12.22,15 12.44,14.97 12.65,14.92L14.2,16.47C13.53,16.8 12.79,17 12,17A5,5 0 0,1 7,12C7,11.21 7.2,10.47 7.53,9.8M2,4.27L4.28,6.55L4.73,7C3.08,8.3 1.78,10 1,12C2.73,16.39 7,19.5 12,19.5C13.55,19.5 15.03,19.2 16.38,18.66L16.81,19.08L19.73,22L21,20.72L3.27,3L2,4.27Z"/>
            </svg>
            <span>Hide</span>
          </button>
        </div>
      </div>
    </div>
  </template>

    <!-- Rule Builder Modal Component -->
    <RuleBuilderModal
      :show="showRuleBuilder"
      :ruleToEdit="ruleToEdit"
      @close="showRuleBuilder = false"
      @saved="fetchRules"
    />

    <!-- Smart Match Modal Component -->
    <SmartMatchModal
      :show="showSmartMatchModal"
      :matches="smartMatches"
      @close="showSmartMatchModal = false"
    />

    <!-- Bulk Hide Domain Modal -->
    <div
      v-if="showBulkHideModal"
      class="bulk-modal-backdrop"
      @click.self="showBulkHideModal = false"
    >
      <div class="bulk-modal-card glass-panel">
        <div class="bulk-modal-header">
          <div>
            <h3 class="bulk-modal-title">🚫 Bulk Hide Entity Types</h3>
            <p class="bulk-modal-subtitle">
              Hide entire categories of Home Assistant entities (e.g. switches, lights, automations) so only relevant security devices appear in your picker.
            </p>
          </div>
          <button class="bulk-modal-close" @click="showBulkHideModal = false" aria-label="Close">✕</button>
        </div>

        <!-- Quick Presets -->
        <div class="preset-action-bar">
          <button
            class="preset-btn primary"
            @click="hideNonSecurityPreset"
            title="Hide switches, lights, automations, scenes, scripts, updates, helpers"
          >
            🛡️ Hide Non-Security Types
          </button>
          <button
            class="preset-btn secondary"
            @click="restoreAllDomains"
            :disabled="entityStore.ignoredDomains.length === 0"
          >
            Show All Types
          </button>
        </div>

        <!-- Search Domains Filter -->
        <div class="bulk-search-box">
          <input
            type="text"
            v-model="domainSearchQuery"
            placeholder="Filter entity types (e.g. switch, light, sensor)..."
            class="bulk-search-input"
          />
        </div>

        <!-- Domain List -->
        <div class="domain-checklist">
          <div
            v-for="item in filteredDetectedDomains"
            :key="item.domain"
            class="domain-check-item"
            :class="{ 'is-ignored': entityStore.isDomainIgnored(item.domain) }"
            @click="toggleDomainIgnore(item.domain)"
          >
            <div class="domain-info-left">
              <input
                type="checkbox"
                :checked="entityStore.isDomainIgnored(item.domain)"
                @click.stop="toggleDomainIgnore(item.domain)"
                class="domain-checkbox"
              />
              <span class="domain-icon">{{ getDomainIcon(item.domain) }}</span>
              <div class="domain-label-group">
                <span class="domain-name">{{ item.domain }}</span>
                <span v-if="isSecurityDomain(item.domain)" class="sec-badge">Security Device</span>
              </div>
            </div>
            <div class="domain-count-badge">
              {{ item.count }} entities
            </div>
          </div>
          <div v-if="filteredDetectedDomains.length === 0" class="empty-domains-msg">
            No entity domains found matching "{{ domainSearchQuery }}".
          </div>
        </div>

        <div class="bulk-modal-footer">
          <div class="hidden-summary-text">
            <strong>{{ entityStore.ignoredDomains.length }}</strong> category(ies) currently hidden
          </div>
          <button class="bulk-done-btn" @click="showBulkHideModal = false">
            Done
          </button>
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
  transition: box-shadow 0.2s ease;
}

.entity-picker.dock-right {
  order: 3;
}

.entity-picker.dock-float {
  position: fixed;
  height: 560px;
  max-height: calc(100vh - 100px);
  z-index: 170;
  box-shadow: 0 16px 40px rgba(0, 0, 0, 0.6), 0 0 0 1px rgba(99, 102, 241, 0.3);
  margin: 0;
}

/* Minimized Floating Pill */
.entity-minimized-pill {
  position: fixed;
  z-index: 250;
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

.entity-minimized-pill.dock-left {
  left: 20px;
  top: 120px;
}

.entity-minimized-pill.dock-right {
  right: 20px;
  top: 120px;
}

.entity-minimized-pill:hover {
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

.picker-header {
  padding: 12px 14px 8px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  cursor: grab;
  user-select: none;
}

.header-info {
  flex: 1;
}

.panel-header-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-left: 6px;
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

.smart-match-banner {
  margin: 0 16px 10px;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.15) 0%, rgba(139, 92, 246, 0.12) 100%);
  border: 1px solid rgba(99, 102, 241, 0.35);
  border-radius: var(--radius-sm, 6px);
  padding: 8px 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  box-shadow: 0 2px 8px rgba(99, 102, 241, 0.1);
}

.banner-text {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.banner-sparkle {
  font-size: 16px;
  flex-shrink: 0;
}

.banner-details {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.banner-title {
  font-size: 11px;
  font-weight: 600;
  color: #a5b4fc;
}

.banner-sub {
  font-size: 10px;
  color: #cbd5e1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.btn-smart-match {
  background: #6366f1;
  color: #ffffff;
  border: none;
  border-radius: 4px;
  padding: 4px 10px;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.15s ease;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.btn-smart-match:hover {
  background: #4f46e5;
  transform: translateY(-1px);
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

.entity-actions-col {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
}

.btn-hide-entity {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  font-size: 10px;
  padding: 2px 5px;
  cursor: pointer;
  opacity: 0.6;
  transition: all 0.15s ease;
}

.entity-item:hover .btn-hide-entity {
  opacity: 1;
}

.btn-hide-entity:hover {
  background: rgba(239, 68, 68, 0.2);
  color: #fca5a5;
  border-color: rgba(239, 68, 68, 0.5);
}

.btn-unhide-entity {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: rgba(99, 102, 241, 0.15);
  border: 1px solid rgba(99, 102, 241, 0.4);
  color: #a5b4fc;
  font-size: 11px;
  font-weight: 500;
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-unhide-entity:hover {
  background: rgba(99, 102, 241, 0.35);
  color: #ffffff;
}

.ignored-item {
  opacity: 0.75;
}

.ignored-pill {
  background: rgba(239, 68, 68, 0.25) !important;
  color: #fca5a5 !important;
}

.hint-text {
  display: block;
  font-size: 11px;
  color: var(--text-secondary);
  margin-top: 6px;
}

/* Bulk Hide Filter Chip in Domain Row */
.bulk-hide-chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  border-color: rgba(239, 68, 68, 0.3) !important;
  color: #fca5a5 !important;
  background: rgba(239, 68, 68, 0.08) !important;
}

.bulk-hide-chip:hover {
  background: rgba(239, 68, 68, 0.2) !important;
  border-color: rgba(239, 68, 68, 0.6) !important;
}

.bulk-hide-chip.has-hidden {
  background: rgba(239, 68, 68, 0.22) !important;
  border-color: #ef4444 !important;
  color: #ffffff !important;
  font-weight: 600;
}

.chip-badge {
  background: #ef4444;
  color: white;
  font-size: 10px;
  padding: 1px 5px;
  border-radius: 8px;
  font-weight: 700;
  line-height: 1.2;
}

/* Bulk Hide Panel inside Ignored Tab */
.ignored-view-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.bulk-hide-panel {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: var(--radius-md);
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.bulk-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.bulk-panel-title {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-primary);
}

.btn-open-bulk-modal {
  background: rgba(99, 102, 241, 0.15);
  border: 1px solid rgba(99, 102, 241, 0.4);
  color: #a5b4fc;
  font-size: 10px;
  font-weight: 600;
  padding: 3px 8px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-open-bulk-modal:hover {
  background: rgba(99, 102, 241, 0.3);
  color: #ffffff;
}

.bulk-quick-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.domain-toggle-pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: var(--radius-sm);
  padding: 3px 6px;
  font-size: 10px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.15s ease;
}

.domain-toggle-pill:hover {
  background: rgba(255, 255, 255, 0.1);
  color: var(--text-primary);
}

.domain-toggle-pill.hidden {
  background: rgba(239, 68, 68, 0.2);
  border-color: rgba(239, 68, 68, 0.6);
  color: #fca5a5;
  font-weight: 600;
}

.pill-icon {
  font-size: 11px;
}

.pill-label {
  font-family: var(--font-mono, monospace);
}

.pill-status {
  font-size: 9px;
  opacity: 0.8;
  padding-left: 2px;
}

.active-hidden-domains {
  background: rgba(239, 68, 68, 0.08);
  border: 1px dashed rgba(239, 68, 68, 0.3);
  border-radius: var(--radius-sm);
  padding: 6px 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.active-domains-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 10px;
  color: #fca5a5;
  font-weight: 600;
}

.hidden-domain-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.hidden-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: rgba(239, 68, 68, 0.25);
  border: 1px solid rgba(239, 68, 68, 0.5);
  border-radius: var(--radius-sm);
  padding: 2px 5px;
  font-size: 10px;
  color: #ffffff;
  font-weight: 500;
}

.tag-close-btn {
  background: transparent;
  border: none;
  color: #fca5a5;
  cursor: pointer;
  font-size: 9px;
  padding: 0 1px;
  line-height: 1;
}

.tag-close-btn:hover {
  color: #ffffff;
}

.btn-text-action {
  background: transparent;
  border: none;
  font-size: 10px;
  color: #a5b4fc;
  cursor: pointer;
  padding: 0;
  text-decoration: underline;
}

.btn-text-action:hover {
  color: #ffffff;
}

.btn-text-action.danger {
  color: #fca5a5;
}

.btn-text-action.danger:hover {
  color: #ef4444;
}

.hidden-entities-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.hidden-section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 2px;
}

.hidden-title {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-primary);
}

.empty-hidden {
  padding: 16px 8px;
}

/* Bulk Hide Modal Overlay */
.bulk-modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  padding: 16px;
}

.bulk-modal-card {
  width: 100%;
  max-width: 480px;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  background: #111827;
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: var(--radius-lg, 12px);
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.6);
  overflow: hidden;
  animation: fadeInModal 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes fadeInModal {
  from {
    opacity: 0;
    transform: scale(0.95) translateY(10px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

.bulk-modal-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 18px 20px 14px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.bulk-modal-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary, #ffffff);
  margin: 0;
}

.bulk-modal-subtitle {
  font-size: 12px;
  color: var(--text-muted, #94a3b8);
  margin: 4px 0 0;
  line-height: 1.4;
}

.bulk-modal-close {
  background: transparent;
  border: none;
  color: var(--text-muted, #94a3b8);
  font-size: 16px;
  cursor: pointer;
  padding: 4px;
  border-radius: var(--radius-sm);
  line-height: 1;
}

.bulk-modal-close:hover {
  color: #ffffff;
  background: rgba(255, 255, 255, 0.1);
}

.preset-action-bar {
  display: flex;
  gap: 8px;
  padding: 12px 20px 8px;
}

.preset-btn {
  flex: 1;
  padding: 7px 10px;
  border-radius: var(--radius-sm, 6px);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
}

.preset-btn.primary {
  background: rgba(239, 68, 68, 0.2);
  border: 1px solid rgba(239, 68, 68, 0.5);
  color: #fca5a5;
}

.preset-btn.primary:hover {
  background: rgba(239, 68, 68, 0.35);
  color: #ffffff;
  border-color: #ef4444;
}

.preset-btn.secondary {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.12);
  color: var(--text-secondary, #cbd5e1);
}

.preset-btn.secondary:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.1);
  color: #ffffff;
}

.preset-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.bulk-search-box {
  padding: 4px 20px 10px;
}

.bulk-search-input {
  width: 100%;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: var(--radius-sm, 6px);
  padding: 8px 12px;
  color: #ffffff;
  font-size: 12px;
  box-sizing: border-box;
}

.bulk-search-input:focus {
  outline: none;
  border-color: var(--color-primary, #6366f1);
  box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.2);
}

.domain-checklist {
  flex: 1;
  overflow-y: auto;
  padding: 0 20px 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-height: 380px;
}

.domain-check-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: var(--radius-sm, 6px);
  cursor: pointer;
  transition: all 0.15s ease;
  user-select: none;
}

.domain-check-item:hover {
  background: rgba(255, 255, 255, 0.07);
  border-color: rgba(255, 255, 255, 0.14);
}

.domain-check-item.is-ignored {
  background: rgba(239, 68, 68, 0.12);
  border-color: rgba(239, 68, 68, 0.35);
}

.domain-info-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.domain-checkbox {
  cursor: pointer;
  accent-color: #ef4444;
  width: 15px;
  height: 15px;
}

.domain-icon {
  font-size: 15px;
}

.domain-label-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.domain-name {
  font-family: var(--font-mono, monospace);
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary, #ffffff);
}

.sec-badge {
  font-size: 9px;
  font-weight: 600;
  color: #34d399;
  background: rgba(52, 211, 153, 0.15);
  border: 1px solid rgba(52, 211, 153, 0.3);
  padding: 1px 5px;
  border-radius: 4px;
}

.domain-count-badge {
  font-size: 11px;
  color: var(--text-muted, #94a3b8);
  font-variant-numeric: tabular-nums;
}

.empty-domains-msg {
  padding: 24px;
  text-align: center;
  color: var(--text-muted, #94a3b8);
  font-size: 12px;
}

.bulk-modal-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(0, 0, 0, 0.2);
}

.hidden-summary-text {
  font-size: 12px;
  color: var(--text-secondary, #cbd5e1);
}

.hidden-summary-text strong {
  color: #ef4444;
}

.bulk-done-btn {
  background: var(--color-primary, #6366f1);
  border: none;
  color: #ffffff;
  padding: 7px 18px;
  border-radius: var(--radius-sm, 6px);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
}

.bulk-done-btn:hover {
  background: #4f46e5;
}
</style>
