<template>
  <Teleport to="body">
    <div v-if="show" class="smart-match-backdrop" @click.self="emit('close')">
      <div class="smart-match-modal">
        <div class="modal-header">
          <div class="header-title">
            <span class="magic-icon">🪄</span>
            <div>
              <h3>Smart Match Room Assignments</h3>
              <p class="subtitle">
                Automatically detected {{ matches.length }} matching room{{ matches.length === 1 ? '' : 's' }} based on keywords, aliases, and abbreviations.
              </p>
            </div>
          </div>
          <button class="btn-close" @click="emit('close')">✕</button>
        </div>

        <div class="modal-body">
          <div v-if="matches.length === 0" class="empty-state">
            <p>No automatic room matches found for current unassigned entities.</p>
          </div>

          <div v-else class="table-container">
            <div class="table-actions">
              <label class="select-all-label">
                <input
                  type="checkbox"
                  :checked="selectedIds.size === matches.length"
                  @change="toggleSelectAll"
                />
                <span>Select All ({{ selectedIds.size }} / {{ matches.length }})</span>
              </label>
              <div class="match-counts">
                <span class="badge high">
                  {{ highConfidenceCount }} High Confidence
                </span>
                <span class="badge medium" v-if="mediumConfidenceCount > 0">
                  {{ mediumConfidenceCount }} Medium Confidence
                </span>
              </div>
            </div>

            <table class="matches-table">
              <thead>
                <tr>
                  <th style="width: 38px"></th>
                  <th>Entity Name & ID</th>
                  <th>Suggested Room</th>
                  <th>Confidence</th>
                  <th>Match Rationale</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="item in matches"
                  :key="item.entity.entity_id"
                  :class="{ selected: selectedIds.has(item.entity.entity_id) }"
                  @click="toggleRow(item.entity.entity_id)"
                >
                  <td @click.stop>
                    <input
                      type="checkbox"
                      :checked="selectedIds.has(item.entity.entity_id)"
                      @change="toggleRow(item.entity.entity_id)"
                    />
                  </td>
                  <td>
                    <div class="entity-name">
                      {{ item.entity.friendly_name || item.entity.name || item.entity.entity_id }}
                    </div>
                    <div class="entity-id">{{ item.entity.entity_id }}</div>
                  </td>
                  <td>
                    <div class="room-pill">
                      📍 {{ item.matchedArea.name }}
                    </div>
                  </td>
                  <td>
                    <span class="confidence-tag" :class="item.confidence">
                      {{ item.confidence === 'high' ? '98% High' : '75% Med' }}
                    </span>
                  </td>
                  <td class="reason-cell">
                    <span class="reason-text">{{ item.reason }}</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div class="modal-footer">
          <button class="btn-cancel" @click="emit('close')" :disabled="isApplying">
            Cancel
          </button>
          <button
            class="btn-apply"
            :disabled="selectedIds.size === 0 || isApplying"
            @click="handleApply"
          >
            <span v-if="isApplying">Applying ({{ applyProgress }} / {{ selectedIds.size }})...</span>
            <span v-else>🪄 Assign {{ selectedIds.size }} Entit{{ selectedIds.size === 1 ? 'y' : 'ies' }}</span>
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, watch } from "vue";
import type { SmartMatchResult } from "../../services/keywordMatcher";
import { useEntityStore } from "../../stores/entityStore";

const props = defineProps<{
  show: boolean;
  matches: SmartMatchResult[];
}>();

const emit = defineEmits<{
  (e: "close"): void;
  (e: "applied", count: number): void;
}>();

const entityStore = useEntityStore();
const selectedIds = ref<Set<string>>(new Set());
const isApplying = ref(false);
const applyProgress = ref(0);

// Initialize selected IDs to all high/medium matches when modal opens
watch(
  () => props.show,
  (open) => {
    if (open) {
      selectedIds.value = new Set(props.matches.map((m) => m.entity.entity_id));
      applyProgress.value = 0;
      isApplying.value = false;
    }
  },
  { immediate: true }
);

const highConfidenceCount = computed(
  () => props.matches.filter((m) => m.confidence === "high").length
);
const mediumConfidenceCount = computed(
  () => props.matches.filter((m) => m.confidence === "medium").length
);

function toggleRow(entityId: string) {
  if (selectedIds.value.has(entityId)) {
    selectedIds.value.delete(entityId);
  } else {
    selectedIds.value.add(entityId);
  }
}

function toggleSelectAll() {
  if (selectedIds.value.size === props.matches.length) {
    selectedIds.value.clear();
  } else {
    selectedIds.value = new Set(props.matches.map((m) => m.entity.entity_id));
  }
}

async function handleApply() {
  if (selectedIds.value.size === 0) return;
  isApplying.value = true;
  applyProgress.value = 0;

  const toApply = props.matches.filter((m) => selectedIds.value.has(m.entity.entity_id));
  let count = 0;

  for (const item of toApply) {
    try {
      await entityStore.designateArea(item.entity.entity_id, item.matchedArea.area_id);
      count++;
      applyProgress.value = count;
    } catch (e) {
      console.warn(`Failed to assign ${item.entity.entity_id}:`, e);
    }
  }

  isApplying.value = false;
  emit("applied", count);
  emit("close");
}
</script>

<style scoped>
.smart-match-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(4px);
  z-index: 10000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.smart-match-modal {
  background: #181920;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 12px;
  width: 100%;
  max-width: 760px;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.6);
  color: #e2e8f0;
  overflow: hidden;
}

.modal-header {
  padding: 16px 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 12px;
}

.magic-icon {
  font-size: 26px;
  background: rgba(99, 102, 241, 0.15);
  padding: 8px;
  border-radius: 8px;
}

.header-title h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #f8fafc;
}

.subtitle {
  margin: 2px 0 0;
  font-size: 12px;
  color: #94a3b8;
}

.btn-close {
  background: transparent;
  border: none;
  color: #94a3b8;
  font-size: 18px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
}
.btn-close:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
}

.modal-body {
  padding: 16px 20px;
  overflow-y: auto;
  flex: 1;
}

.table-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  padding: 0 4px;
}

.select-all-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #cbd5e1;
  cursor: pointer;
}

.match-counts {
  display: flex;
  gap: 8px;
}

.badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 9999px;
  font-weight: 500;
}
.badge.high {
  background: rgba(16, 185, 129, 0.15);
  color: #34d399;
  border: 1px solid rgba(16, 185, 129, 0.3);
}
.badge.medium {
  background: rgba(245, 158, 11, 0.15);
  color: #fbbf24;
  border: 1px solid rgba(245, 158, 11, 0.3);
}

.table-container {
  overflow-x: auto;
}

.matches-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.matches-table th {
  text-align: left;
  padding: 8px 12px;
  color: #94a3b8;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  font-weight: 500;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.matches-table td {
  padding: 10px 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
  vertical-align: middle;
}

.matches-table tr:hover {
  background: rgba(255, 255, 255, 0.03);
  cursor: pointer;
}

.matches-table tr.selected {
  background: rgba(99, 102, 241, 0.06);
}

.entity-name {
  font-weight: 500;
  color: #f1f5f9;
}

.entity-id {
  font-size: 11px;
  color: #64748b;
  font-family: monospace;
}

.room-pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: rgba(99, 102, 241, 0.12);
  color: #818cf8;
  padding: 3px 8px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
}

.confidence-tag {
  display: inline-block;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
}
.confidence-tag.high {
  background: rgba(16, 185, 129, 0.12);
  color: #10b981;
}
.confidence-tag.medium {
  background: rgba(245, 158, 11, 0.12);
  color: #f59e0b;
}

.reason-cell {
  font-size: 11px;
  color: #94a3b8;
}

.modal-footer {
  padding: 14px 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  background: #14151b;
}

.btn-cancel {
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.15);
  color: #cbd5e1;
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
}
.btn-cancel:hover {
  background: rgba(255, 255, 255, 0.05);
}

.btn-apply {
  background: #6366f1;
  border: none;
  color: #fff;
  padding: 8px 18px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: background 0.15s;
}
.btn-apply:hover:not(:disabled) {
  background: #4f46e5;
}
.btn-apply:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.empty-state {
  text-align: center;
  padding: 30px 20px;
  color: #94a3b8;
}
</style>
