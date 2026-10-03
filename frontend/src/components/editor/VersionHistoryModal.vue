<script setup lang="ts">
import { ref, onMounted } from "vue";
import { api } from "@/services/api";
import { usePlanStore } from "@/stores/planStore";

const props = defineProps<{
  planId: string;
}>();

const emit = defineEmits<{
  (e: "close"): void;
  (e: "restored"): void;
}>();

const planStore = usePlanStore();

interface VersionItem {
  filename: string;
  modified: number;
  size: number;
}

const versions = ref<VersionItem[]>([]);
const isLoading = ref(true);
const isRestoring = ref(false);
const error = ref<string | null>(null);

async function loadVersions() {
  isLoading.value = true;
  error.value = null;
  try {
    const res = await api.listVersions(props.planId);
    versions.value = res.versions.sort((a, b) => b.modified - a.modified);
  } catch (err: any) {
    error.value = err.message || "Failed to load versions";
  } finally {
    isLoading.value = false;
  }
}

async function handleRestore(versionFilename: string) {
  if (!confirm(`Restore floor plan to snapshot '${versionFilename}'? Current state will be backed up first.`)) {
    return;
  }

  isRestoring.value = true;
  try {
    const res = await api.restoreVersion(props.planId, versionFilename);
    planStore.site = res.plan;
    emit("restored");
    emit("close");
  } catch (err: any) {
    alert(err.message || "Failed to restore version");
  } finally {
    isRestoring.value = false;
  }
}

function formatTime(timestampSec: number): string {
  const date = new Date(timestampSec * 1000);
  return date.toLocaleString();
}

function formatRelative(timestampSec: number): string {
  const diffSec = Math.round((Date.now() - timestampSec * 1000) / 1000);
  if (diffSec < 60) return "Just now";
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`;
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`;
  return `${Math.floor(diffSec / 86400)}d ago`;
}

function formatSize(bytes: number): string {
  return `${(bytes / 1024).toFixed(1)} KB`;
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === "Escape") {
    emit("close");
  }
}

onMounted(() => {
  loadVersions();
  window.addEventListener("keydown", handleKeydown);
});
</script>

<template>
  <div class="modal-backdrop" @click.self="emit('close')">
    <div class="version-modal glass-panel">
      <div class="modal-header">
        <div class="header-info">
          <h3>Version Rollback History</h3>
          <p>Rolling 20 version snapshots automatically recorded on save.</p>
        </div>
        <button class="close-btn" @click="emit('close')">×</button>
      </div>

      <div class="modal-body">
        <div v-if="isLoading" class="state-msg">Loading version history...</div>
        <div v-else-if="error" class="state-msg error">{{ error }}</div>
        <div v-else-if="versions.length === 0" class="state-msg">
          No prior versions recorded yet. Versions are created automatically each time changes are saved.
        </div>

        <div v-else class="version-list">
          <div
            v-for="(ver, idx) in versions"
            :key="ver.filename"
            class="version-item"
          >
            <div class="ver-meta">
              <div class="ver-title">
                <span class="ver-badge">#{{ versions.length - idx }}</span>
                <span class="ver-relative">{{ formatRelative(ver.modified) }}</span>
                <span class="ver-size">{{ formatSize(ver.size) }}</span>
              </div>
              <div class="ver-date">{{ formatTime(ver.modified) }}</div>
            </div>

            <button
              class="restore-btn"
              :disabled="isRestoring"
              @click="handleRestore(ver.filename)"
            >
              ↺ Rollback to this Version
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.75);
  backdrop-filter: blur(4px);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.version-modal {
  width: 100%;
  max-width: 580px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  border-radius: var(--radius-lg);
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.6);
  border: 1px solid var(--border-color);
  overflow: hidden;
}

.modal-header {
  padding: 16px 20px;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  border-bottom: 1px solid var(--border-color);
}

.header-info h3 {
  margin: 0 0 4px;
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.header-info p {
  margin: 0;
  font-size: 12px;
  color: var(--text-muted);
}

.close-btn {
  font-size: 24px;
  line-height: 1;
  color: var(--text-muted);
  cursor: pointer;
}

.close-btn:hover {
  color: var(--text-primary);
}

.modal-body {
  padding: 16px 20px;
  overflow-y: auto;
  flex: 1;
}

.state-msg {
  text-align: center;
  padding: 30px 10px;
  color: var(--text-muted);
  font-size: 13px;
}

.state-msg.error {
  color: var(--color-danger);
}

.version-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.version-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 14px;
  background: rgba(30, 41, 59, 0.7);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  transition: all 0.15s ease;
}

.version-item:hover {
  border-color: rgba(99, 102, 241, 0.4);
  background: rgba(30, 41, 59, 0.95);
}

.ver-meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.ver-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.ver-badge {
  font-size: 11px;
  padding: 1px 6px;
  background: rgba(99, 102, 241, 0.2);
  color: #818cf8;
  border-radius: 4px;
  font-weight: 600;
}

.ver-relative {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.ver-size {
  font-size: 11px;
  color: var(--text-muted);
  font-family: var(--font-mono);
}

.ver-date {
  font-size: 11px;
  color: var(--text-secondary);
}

.restore-btn {
  padding: 6px 12px;
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
  border-radius: var(--radius-sm);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
}

.restore-btn:hover:not(:disabled) {
  background: var(--accent-primary);
  color: #ffffff;
  border-color: var(--accent-primary);
}

.restore-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
