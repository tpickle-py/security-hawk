<script setup lang="ts">
import { ref, onMounted, onUnmounted } from "vue";
import { useEditorStore } from "@/stores/editorStore";
import { usePlanStore } from "@/stores/planStore";
import { useHistoryStore } from "@/stores/historyStore";
import { api } from "@/services/api";
import VersionHistoryModal from "@/components/editor/VersionHistoryModal.vue";

const editorStore = useEditorStore();
const planStore = usePlanStore();
const historyStore = useHistoryStore();

const fileInputRef = ref<HTMLInputElement | null>(null);
const importFileInputRef = ref<HTMLInputElement | null>(null);
const isUploading = ref(false);
const isImporting = ref(false);
const showVersionModal = ref(false);

function triggerUpload() {
  fileInputRef.value?.click();
}

function triggerImport() {
  importFileInputRef.value?.click();
}

function handleExportPlan() {
  if (!planStore.currentPlanId) return;
  const url = api.getExportUrl(planStore.currentPlanId);
  window.open(url, "_blank");
}

async function handleImportFileChange(e: Event) {
  const target = e.target as HTMLInputElement;
  const file = target.files?.[0];
  if (!file || !planStore.currentPlanId) return;

  isImporting.value = true;
  try {
    const res = await api.importPlan(file, planStore.currentPlanId);
    await planStore.loadPlan(planStore.currentPlanId);
    alert(`Successfully imported floor plan (${res.migrated ? "schema upgraded" : "ready"})`);
  } catch (err: any) {
    alert(err.message || "Failed to import plan");
  } finally {
    isImporting.value = false;
    if (target) target.value = "";
  }
}

async function handleFileChange(e: Event) {
  const target = e.target as HTMLInputElement;
  const file = target.files?.[0];
  if (!file || !planStore.currentPlanId) return;

  isUploading.value = true;
  try {
    const uploaded = await api.uploadAsset(planStore.currentPlanId, file);

    // Get image dimensions
    let width = 1200;
    let height = 800;

    if (file.type.startsWith("image/")) {
      const img = new Image();
      const objectUrl = URL.createObjectURL(file);
      await new Promise((resolve) => {
        img.onload = () => {
          width = img.naturalWidth || 1200;
          height = img.naturalHeight || 800;
          URL.revokeObjectURL(objectUrl);
          resolve(true);
        };
        img.onerror = () => {
          URL.revokeObjectURL(objectUrl);
          resolve(false);
        };
        img.src = objectUrl;
      });
    }

    planStore.setBackground({
      asset_id: uploaded.asset_id,
      filename: uploaded.filename,
      original_name: uploaded.original_name,
      url: uploaded.url,
      x: 0,
      y: 0,
      width,
      height,
      rotation: 0,
      locked: true,
    });
  } catch (err: any) {
    alert(err.message || "Upload failed");
  } finally {
    isUploading.value = false;
    if (target) target.value = "";
  }
}

function handleKeyDown(e: KeyboardEvent) {
  const tag = (e.target as HTMLElement)?.tagName?.toLowerCase();
  if (tag === "input" || tag === "textarea") return;

  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "z") {
    if (e.shiftKey) {
      if (historyStore.canRedo) {
        e.preventDefault();
        planStore.performRedo();
      }
    } else {
      if (historyStore.canUndo) {
        e.preventDefault();
        planStore.performUndo();
      }
    }
  } else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "y") {
    if (historyStore.canRedo) {
      e.preventDefault();
      planStore.performRedo();
    }
  }
}

onMounted(() => {
  window.addEventListener("keydown", handleKeyDown);
});

onUnmounted(() => {
  window.removeEventListener("keydown", handleKeyDown);
});
</script>

<template>
  <div class="toolbar glass-panel">
    <!-- Tool selection -->
    <div class="tool-group">
      <button
        class="tool-btn"
        :class="{ active: editorStore.activeTool === 'select' }"
        title="Select & Move (V)"
        @click="editorStore.setTool('select')"
      >
        <svg viewBox="0 0 24 24" width="18" height="18">
          <path fill="currentColor" d="M4 3l12 12-5.5.5 3 6.5-2.5 1-3-6.5-4 4V3z"/>
        </svg>
      </button>

      <button
        class="tool-btn"
        :class="{ active: editorStore.activeTool === 'pan' }"
        title="Pan Canvas (H)"
        @click="editorStore.setTool('pan')"
      >
        <svg viewBox="0 0 24 24" width="18" height="18">
          <path fill="currentColor" d="M10 5a1 1 0 0 1 2 0v5a1 1 0 0 1-2 0V5zm-4 4a1 1 0 0 1 2 0v5a1 1 0 0 1-2 0V9zm8-2a1 1 0 0 1 2 0v5a1 1 0 0 1-2 0V7zm4 4a1 1 0 0 1 2 0v5a1 1 0 0 1-2 0v-5zM2 13a1 1 0 0 1 2 0v3a6 6 0 0 0 6 6h4a6 6 0 0 0 6-6v-3a1 1 0 1 1 2 0v3a8 8 0 0 1-8 8h-4a8 8 0 0 1-8-8v-3z"/>
        </svg>
      </button>

      <button
        class="tool-btn"
        :class="{ active: editorStore.isSettingScale }"
        title="Calibrate Scale"
        @click="editorStore.startScaleCalibration"
      >
        <svg viewBox="0 0 24 24" width="18" height="18">
          <path fill="currentColor" d="M1.5 8l3-3 18 18-3 3-18-18zm3.5.5l1.5 1.5-1.5 1.5 1.5 1.5-1.5 1.5 1.5 1.5-1.5 1.5 1.5 1.5-1.5 1.5 1.5 1.5-1.5 1.5 1.5 1.5"/>
        </svg>
      </button>
    </div>

    <div class="divider"></div>

    <!-- Undo / Redo & Version History -->
    <div class="tool-group">
      <button
        class="tool-btn"
        :disabled="!historyStore.canUndo"
        title="Undo (Ctrl+Z)"
        @click="planStore.performUndo()"
      >
        <svg viewBox="0 0 24 24" width="18" height="18">
          <path fill="currentColor" d="M12.5 8c-2.65 0-5.05 1-6.9 2.6L2 7v9h9l-3.62-3.62c1.39-1.16 3.16-1.88 5.12-1.88 3.54 0 6.55 2.31 7.6 5.5l2.37-.78C21.08 11.03 17.15 8 12.5 8z"/>
        </svg>
      </button>

      <button
        class="tool-btn"
        :disabled="!historyStore.canRedo"
        title="Redo (Ctrl+Y)"
        @click="planStore.performRedo()"
      >
        <svg viewBox="0 0 24 24" width="18" height="18">
          <path fill="currentColor" d="M18.4 10.6C16.55 9 14.15 8 11.5 8c-4.65 0-8.58 3.03-9.96 7.22L3.9 16c1.05-3.19 4.05-5.5 7.6-5.5 1.95 0 3.73.72 5.12 1.88L13 16h9V7l-3.6 3.6z"/>
        </svg>
      </button>

      <button
        class="tool-btn"
        title="Version History (Rolling 20 Snapshots)"
        @click="showVersionModal = true"
      >
        <svg viewBox="0 0 24 24" width="18" height="18">
          <path fill="currentColor" d="M13 3a9 9 0 0 0-9 9H1l3.89 3.89.07.14L9 12H6c0-3.87 3.13-7 7-7s7 3.13 7 7-3.13 7-7 7c-1.93 0-3.68-.79-4.94-2.06l-1.42 1.42A8.954 8.954 0 0 0 13 21a9 9 0 0 0 0-18zm-1 5v5l4.25 2.52.77-1.28-3.52-2.09V8z"/>
        </svg>
      </button>
    </div>

    <div class="divider"></div>

    <!-- Zoom controls -->
    <div class="tool-group">
      <button class="tool-btn" title="Zoom In" @click="editorStore.zoomIn">
        <svg viewBox="0 0 24 24" width="18" height="18"><path fill="currentColor" d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/></svg>
      </button>
      <span class="zoom-level">{{ Math.round(editorStore.zoom * 100) }}%</span>
      <button class="tool-btn" title="Zoom Out" @click="editorStore.zoomOut">
        <svg viewBox="0 0 24 24" width="18" height="18"><path fill="currentColor" d="M19 13H5v-2h14v2z"/></svg>
      </button>
      <button class="tool-btn" title="Reset View" @click="editorStore.resetView">
        <svg viewBox="0 0 24 24" width="18" height="18"><path fill="currentColor" d="M12 4V1L8 5l4 4V6c3.31 0 6 2.69 6 6 0 1.01-.25 1.97-.7 2.8l1.46 1.46A7.93 7.93 0 0 0 20 12c0-4.42-3.58-8-8-8zm0 14c-3.31 0-6-2.69-6-6 0-1.01.25-1.97.7-2.8L5.24 7.74A7.93 7.93 0 0 0 4 12c0 4.42 3.58 8 8 8v3l4-4-4-4v3z"/></svg>
      </button>
    </div>

    <div class="divider"></div>

    <!-- Export / Import / Background upload -->
    <div class="tool-group">
      <button class="tool-btn action" title="Export Plan JSON (Backup/Testing)" @click="handleExportPlan">
        <svg viewBox="0 0 24 24" width="16" height="16">
          <path fill="currentColor" d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/>
        </svg>
        <span>Export</span>
      </button>

      <button class="tool-btn action" :disabled="isImporting" title="Import Plan JSON (with Auto-Migration)" @click="triggerImport">
        <svg viewBox="0 0 24 24" width="16" height="16">
          <path fill="currentColor" d="M9 16h6v-6h4l-7-7-7 7h4v6zm-4 2h14v2H5v-2z"/>
        </svg>
        <span>{{ isImporting ? 'Importing...' : 'Import' }}</span>
      </button>
      <input
        ref="importFileInputRef"
        type="file"
        accept=".json,application/json"
        style="display: none;"
        @change="handleImportFileChange"
      />

      <button class="tool-btn action" :disabled="isUploading" @click="triggerUpload">
        <svg viewBox="0 0 24 24" width="16" height="16">
          <path fill="currentColor" d="M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96zM14 13v4h-4v-4H7l5-5 5 5h-3z"/>
        </svg>
        <span>{{ isUploading ? 'Uploading...' : 'Background' }}</span>
      </button>
      <input
        ref="fileInputRef"
        type="file"
        accept=".svg,.png,.jpg,.jpeg,.webp"
        style="display: none;"
        @change="handleFileChange"
      />
    </div>

    <!-- Save status -->
    <div class="save-status">
      <span v-if="planStore.isSaving" class="status-saving">Saving...</span>
      <span v-else-if="planStore.lastSavedAt" class="status-saved">Saved</span>
    </div>

    <!-- Version History Modal -->
    <VersionHistoryModal
      v-if="showVersionModal && planStore.currentPlanId"
      :plan-id="planStore.currentPlanId"
      @close="showVersionModal = false"
    />
  </div>
</template>

<style scoped>
.toolbar {
  position: absolute;
  top: 16px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  z-index: 100;
}

.tool-group {
  display: flex;
  align-items: center;
  gap: 4px;
}

.divider {
  width: 1px;
  height: 20px;
  background-color: var(--border-color);
  margin: 0 4px;
}

.tool-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 6px 10px;
  color: var(--text-secondary);
  border-radius: var(--radius-sm);
  font-size: 13px;
  font-weight: 500;
}

.tool-btn:hover:not(:disabled) {
  background: var(--bg-surface);
  color: var(--text-primary);
}

.tool-btn.active {
  background: var(--accent-primary);
  color: #ffffff;
  box-shadow: 0 0 10px var(--accent-primary-glow);
}

.tool-btn.action {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
}

.tool-btn.action:hover:not(:disabled) {
  border-color: var(--accent-primary);
}

.zoom-level {
  font-size: 12px;
  color: var(--text-muted);
  width: 42px;
  text-align: center;
  font-family: var(--font-mono);
}

.save-status {
  margin-left: 8px;
  font-size: 11px;
  color: var(--text-muted);
  min-width: 48px;
}

.status-saving {
  color: var(--color-warning);
}

.status-saved {
  color: var(--color-success);
}
</style>
