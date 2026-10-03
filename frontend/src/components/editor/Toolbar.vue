<script setup lang="ts">
import { ref } from "vue";
import { useEditorStore } from "@/stores/editorStore";
import { usePlanStore } from "@/stores/planStore";
import { api } from "@/services/api";

const editorStore = useEditorStore();
const planStore = usePlanStore();

const fileInputRef = ref<HTMLInputElement | null>(null);
const isUploading = ref(false);

function triggerUpload() {
  fileInputRef.value?.click();
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

    <!-- Background upload -->
    <div class="tool-group">
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
