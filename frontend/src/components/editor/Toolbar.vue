<script setup lang="ts">
import { ref, onMounted, onUnmounted } from "vue";
import { useEditorStore, VIEWPORT_CONFIGS, type ViewportPreset } from "@/stores/editorStore";
import { usePlanStore } from "@/stores/planStore";
import { useHistoryStore } from "@/stores/historyStore";
import { api } from "@/services/api";
const editorStore = useEditorStore();
const planStore = usePlanStore();
const historyStore = useHistoryStore();

const fileInputRef = ref<HTMLInputElement | null>(null);
const importFileInputRef = ref<HTMLInputElement | null>(null);
const isUploading = ref(false);
const isImporting = ref(false);
const showViewportMenu = ref(false);

function selectViewportPreset(preset: ViewportPreset) {
  editorStore.setViewport(preset);
  showViewportMenu.value = false;
}

function handleRecenterItems() {
  const selectedIds = editorStore.selectedEndpointIds;
  if (selectedIds.length > 0) {
    planStore.recenterEndpoints(selectedIds);
  } else {
    planStore.recenterEndpoints();
  }
}

function handleFitView() {
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
    minX = Math.min(minX, ep.x - 20);
    maxX = Math.max(maxX, ep.x + 20);
    minY = Math.min(minY, ep.y - 20);
    maxY = Math.max(maxY, ep.y + 20);
  }

  const containerW = window.innerWidth - 380;
  const containerH = window.innerHeight - 80;

  editorStore.fitToView(containerW, containerH, {
    minX: minX === Infinity ? 0 : minX,
    maxX: maxX === -Infinity ? 1200 : maxX,
    minY: minY === Infinity ? 0 : minY,
    maxY: maxY === -Infinity ? 800 : maxY,
  });
}

function triggerUpload() {
  fileInputRef.value?.click();
}

function triggerImport() {
  importFileInputRef.value?.click();
}

function handleExportPlan() {
  editorStore.showExportModal = true;
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

  // Undo / Redo
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
    return;
  } else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "y") {
    if (historyStore.canRedo) {
      e.preventDefault();
      planStore.performRedo();
    }
    return;
  }

  // Escape cancels drawing or returns to select tool
  if (e.key === "Escape") {
    editorStore.drawingPoints = [];
    editorStore.setTool("select");
    editorStore.clearSelection();
    return;
  }

  // Single-key shortcuts
  if (!e.ctrlKey && !e.metaKey && !e.altKey) {
    const k = e.key.toLowerCase();
    if (k === "v") editorStore.setTool("select");
    else if (k === "h") editorStore.setTool("pan");
    else if (k === "w") editorStore.setTool("wall");
    else if (k === "r") editorStore.setTool("room");
    else if (k === "d") editorStore.setTool("door");
    else if (k === "n") editorStore.setTool("window");
    else if (k === "t") editorStore.setTool("label");
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
  <div :class="['toolbar', 'glass-panel', `dock-${editorStore.toolbarDock}`]">
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

    <!-- Drawing Tools -->
    <div class="tool-group">
      <button
        class="tool-btn"
        :class="{ active: editorStore.activeTool === 'wall' }"
        title="Draw Wall (W) - Click two points, Shift to chain"
        @click="editorStore.setTool('wall')"
      >
        <svg viewBox="0 0 24 24" width="18" height="18">
          <path fill="currentColor" d="M19 4H5a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2zm0 4h-4V6h4v2zm-6 0H9V6h4v2zM5 6h2v2H5V6zm0 4h6v2H5v-2zm8 0h6v2h-6v-2zm-2 4H5v-2h6v2zm2 0v-2h6v2h-6zm4 4h-4v-2h4v2zm-6 0H9v-2h4v2zM5 16h2v2H5v-2z"/>
        </svg>
      </button>

      <button
        class="tool-btn"
        :class="{ active: editorStore.activeTool === 'room' }"
        title="Room Polygon (R) - Click vertices, double-click to close"
        @click="editorStore.setTool('room')"
      >
        <svg viewBox="0 0 24 24" width="18" height="18">
          <path fill="currentColor" d="M19 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V5a2 2 0 0 0-2-2zm-1 16H6a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1h12a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1z"/>
        </svg>
      </button>

      <button
        class="tool-btn"
        title="Insert Room & Subsection Grid (Table matrix picker for rooms / closets)"
        @click="editorStore.showRoomGridModal = true"
      >
        <svg viewBox="0 0 24 24" width="18" height="18">
          <path fill="currentColor" d="M3 3v18h18V3H3zm8 8H5V5h6v6zm2-6h6v6h-6V5zm-2 8v6H5v-6h6zm2 6v-6h6v6h-6z"/>
        </svg>
      </button>

      <button
        class="tool-btn"
        :class="{ active: editorStore.activeTool === 'door' }"
        title="Door Cutout (D) - Click existing wall to place door"
        @click="editorStore.setTool('door')"
      >
        <svg viewBox="0 0 24 24" width="18" height="18">
          <path fill="currentColor" d="M19 19V5c0-1.1-.9-2-2-2H7c-1.1 0-2 .9-2 2v14H3v2h18v-2h-2zm-4-2H7V5h8v12zm-3-7c-.55 0-1 .45-1 1s.45 1 1 1 1-.45 1-1-.45-1-1-1z"/>
        </svg>
      </button>

      <button
        class="tool-btn"
        :class="{ active: editorStore.activeTool === 'window' }"
        title="Window Cutout (N) - Click existing wall to place window"
        @click="editorStore.setTool('window')"
      >
        <svg viewBox="0 0 24 24" width="18" height="18">
          <path fill="currentColor" d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-8 8H5V5h6v6zm2-6h6v6h-6V5zm-2 8v6H5v-6h6zm2 6v-6h6v6h-6z"/>
        </svg>
      </button>

      <button
        class="tool-btn"
        :class="{ active: editorStore.activeTool === 'label' }"
        title="Text Label (T) - Click canvas to place architectural text"
        @click="editorStore.setTool('label')"
      >
        <svg viewBox="0 0 24 24" width="18" height="18">
          <path fill="currentColor" d="M5 4v3h5.5v12h3V7H19V4H5z"/>
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
        @click="editorStore.showVersionModal = true"
      >
        <svg viewBox="0 0 24 24" width="18" height="18">
          <path fill="currentColor" d="M13 3a9 9 0 0 0-9 9H1l3.89 3.89.07.14L9 12H6c0-3.87 3.13-7 7-7s7 3.13 7 7-3.13 7-7 7c-1.93 0-3.68-.79-4.94-2.06l-1.42 1.42A8.954 8.954 0 0 0 13 21a9 9 0 0 0 0-18zm-1 5v5l4.25 2.52.77-1.28-3.52-2.09V8z"/>
        </svg>
      </button>
    </div>

    <div class="divider"></div>

    <!-- Zoom & Fit controls -->
    <div class="tool-group">
      <button class="tool-btn" title="Zoom In" @click="editorStore.zoomIn">
        <svg viewBox="0 0 24 24" width="18" height="18"><path fill="currentColor" d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/></svg>
      </button>
      <span class="zoom-level">{{ Math.round(editorStore.zoom * 100) }}%</span>
      <button class="tool-btn" title="Zoom Out" @click="editorStore.zoomOut">
        <svg viewBox="0 0 24 24" width="18" height="18"><path fill="currentColor" d="M19 13H5v-2h14v2z"/></svg>
      </button>
      <button class="tool-btn" title="Reset View Zoom" @click="editorStore.resetView">
        <svg viewBox="0 0 24 24" width="18" height="18"><path fill="currentColor" d="M12 4V1L8 5l4 4V6c3.31 0 6 2.69 6 6 0 1.01-.25 1.97-.7 2.8l1.46 1.46A7.93 7.93 0 0 0 20 12c0-4.42-3.58-8-8-8zm0 14c-3.31 0-6-2.69-6-6 0-1.01.25-1.97.7-2.8L5.24 7.74A7.93 7.93 0 0 0 4 12c0 4.42 3.58 8 8 8v3l4-4-4-4v3z"/></svg>
      </button>
      <button class="tool-btn" title="Fit View to Screen" @click="handleFitView">
        <svg viewBox="0 0 24 24" width="16" height="16"><path fill="currentColor" d="M5 5h5V3H3v7h2V5zm14-2h-7v2h5v5h2V3zm0 14h-2v5h-5v2h7v-7zM5 14H3v7h7v-2H5v-5z"/></svg>
      </button>
    </div>

    <div class="divider"></div>

    <!-- Recenter Items -->
    <div class="tool-group">
      <button
        class="tool-btn action recenter-btn"
        :title="editorStore.selectedEndpointIds.length > 0 ? 'Recenter selected items on floor plan' : 'Recenter all items on floor plan'"
        @click="handleRecenterItems"
      >
        <svg viewBox="0 0 24 24" width="15" height="15">
          <path fill="currentColor" d="M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2zm0 18a8 8 0 1 1 8-8 8 8 0 0 1-8 8zm0-13a5 5 0 1 0 5 5 5 5 0 0 0-5-5zm0 8a3 3 0 1 1 3-3 3 3 0 0 1-3 3z"/>
        </svg>
        <span>{{ editorStore.selectedEndpointIds.length > 0 ? `Recenter (${editorStore.selectedEndpointIds.length})` : 'Recenter' }}</span>
      </button>
    </div>

    <div class="divider"></div>

    <!-- Viewport Aspect Simulator -->
    <div class="tool-group relative-container">
      <button
        class="tool-btn action viewport-btn"
        :class="{ active: editorStore.activeViewport !== 'freeform' }"
        title="Simulate different screen aspect ratios (Phone, Tablet, TV)"
        @click="showViewportMenu = !showViewportMenu"
      >
        <span>{{ VIEWPORT_CONFIGS[editorStore.activeViewport]?.icon }}</span>
        <span>{{ VIEWPORT_CONFIGS[editorStore.activeViewport]?.aspectRatio || 'Aspect' }}</span>
        <svg viewBox="0 0 24 24" width="12" height="12"><path fill="currentColor" d="M7 10l5 5 5-5z"/></svg>
      </button>

      <!-- Viewport Presets Dropdown Menu -->
      <div v-if="showViewportMenu" class="viewport-menu glass-panel" @click.stop>
        <div class="menu-header">Preview Screen Aspect</div>
        <button
          v-for="vp in Object.values(VIEWPORT_CONFIGS)"
          :key="vp.id"
          class="viewport-menu-item"
          :class="{ active: editorStore.activeViewport === vp.id }"
          @click="selectViewportPreset(vp.id)"
        >
          <span class="vp-icon">{{ vp.icon }}</span>
          <div class="vp-meta">
            <span class="vp-name">{{ vp.label }}</span>
            <span class="vp-aspect" v-if="vp.width > 0">{{ vp.width }}×{{ vp.height }}px ({{ vp.aspectRatio }})</span>
            <span class="vp-aspect" v-else>Freeform / Full Canvas</span>
          </div>
          <span v-if="editorStore.activeViewport === vp.id" class="vp-check">✓</span>
        </button>
      </div>
    </div>

    <div class="divider"></div>

    <!-- Export / Import / Background upload -->
    <div class="tool-group">
      <button class="tool-btn action" title="Export Floor Plan (.zip Bundle or .json)" @click="handleExportPlan">
        <svg viewBox="0 0 24 24" width="16" height="16">
          <path fill="currentColor" d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/>
        </svg>
        <span>Export</span>
      </button>

      <button class="tool-btn action" :disabled="isImporting" title="Import Plan .zip Bundle or .json" @click="triggerImport">
        <svg viewBox="0 0 24 24" width="16" height="16">
          <path fill="currentColor" d="M9 16h6v-6h4l-7-7-7 7h4v6zm-4 2h14v2H5v-2z"/>
        </svg>
        <span>{{ isImporting ? 'Importing...' : 'Import' }}</span>
      </button>
      <input
        ref="importFileInputRef"
        type="file"
        accept=".json,.zip,application/json,application/zip,application/x-zip-compressed"
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

    <div class="divider"></div>

    <!-- Quick Dock Position Button -->
    <div class="tool-group">
      <button
        class="tool-btn dock-toggle-btn"
        :title="`Toolbar docked: ${editorStore.toolbarDock.toUpperCase()}. Click to cycle position (Top, Right, Bottom, Left)`"
        @click="editorStore.cycleToolbarDock()"
      >
        <span>⚓</span>
      </button>

      <!-- Toggle AutoCAD Command Bar -->
      <button
        class="tool-btn action"
        :class="{ active: editorStore.showCadCommandBar }"
        title="Toggle AutoCAD Command Line (Command bar, shortcuts, helper)"
        @click="editorStore.toggleCadCommandBar"
      >
        <span>⌨️</span>
        <span>AutoCAD</span>
      </button>

      <!-- Security Coverage Audit (AI / MCP) -->
      <button
        class="tool-btn action audit-btn"
        title="AI & Rules Security Coverage Audit (Identify blind spots, unmonitored doors)"
        @click="editorStore.showCoverageAuditModal = true"
      >
        <span>🛡️</span>
        <span>Audit</span>
      </button>

      <!-- Workspace Presets Switcher -->
      <div class="workspace-presets">
        <button
          class="preset-btn"
          :class="{ active: editorStore.activeWorkspacePreset === 'mapping' }"
          title="Mapping Mode: Standard dual sidebars for setup"
          @click="editorStore.setWorkspacePreset('mapping')"
        >
          🗺️
        </button>
        <button
          class="preset-btn"
          :class="{ active: editorStore.activeWorkspacePreset === 'cad' }"
          title="CAD Focus Mode: Command line prompt, sidebars collapsed"
          @click="editorStore.setWorkspacePreset('cad')"
        >
          ⌨️
        </button>
        <button
          class="preset-btn"
          :class="{ active: editorStore.activeWorkspacePreset === 'zen' }"
          title="Zen Mode: Edge-to-edge canvas with all panels minimized"
          @click="editorStore.setWorkspacePreset('zen')"
        >
          🧘
        </button>
      </div>
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
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  z-index: 100;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

/* Docking Positions */
.toolbar.dock-top {
  top: 16px;
  left: 50%;
  transform: translateX(-50%);
  flex-direction: row;
}

.toolbar.dock-bottom {
  bottom: 16px;
  left: 50%;
  transform: translateX(-50%);
  flex-direction: row;
}

.toolbar.dock-left {
  left: 16px;
  top: 50%;
  transform: translateY(-50%);
  flex-direction: column;
  padding: 10px 6px;
  max-height: calc(100vh - 100px);
  overflow-y: auto;
}

.toolbar.dock-right {
  right: 16px;
  top: 50%;
  transform: translateY(-50%);
  flex-direction: column;
  padding: 10px 6px;
  max-height: calc(100vh - 100px);
  overflow-y: auto;
}

/* Vertical Dock Adjustments */
.toolbar.dock-left .tool-group,
.toolbar.dock-right .tool-group {
  flex-direction: column;
  gap: 5px;
}

.toolbar.dock-left .divider,
.toolbar.dock-right .divider {
  width: 20px;
  height: 1px;
  margin: 4px 0;
}

.toolbar.dock-left .tool-btn.action span:not(.vp-icon),
.toolbar.dock-right .tool-btn.action span:not(.vp-icon),
.toolbar.dock-left .save-status,
.toolbar.dock-right .save-status {
  display: none;
}

.dock-toggle-btn {
  font-size: 13px;
  padding: 6px 8px;
  color: var(--text-secondary);
}

.dock-toggle-btn:hover {
  color: #a5b4fc;
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

.tool-btn.audit-btn {
  background: rgba(16, 185, 129, 0.12);
  border-color: rgba(16, 185, 129, 0.3);
  color: #34d399;
}
.tool-btn.audit-btn:hover {
  background: rgba(16, 185, 129, 0.22);
  border-color: #34d399;
}

.workspace-presets {
  display: flex;
  background: rgba(0, 0, 0, 0.25);
  border-radius: var(--radius-sm, 6px);
  padding: 2px;
  gap: 2px;
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.preset-btn {
  background: transparent;
  border: none;
  border-radius: 4px;
  padding: 4px 6px;
  font-size: 13px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s ease;
  opacity: 0.65;
}
.preset-btn:hover {
  opacity: 1;
  background: rgba(255, 255, 255, 0.08);
}
.preset-btn.active {
  opacity: 1;
  background: var(--accent-primary, #6366f1);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
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

.relative-container {
  position: relative;
}

.viewport-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
}

.viewport-btn.active {
  background: rgba(99, 102, 241, 0.2);
  border-color: #6366f1;
  color: #ffffff;
}

.recenter-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.recenter-btn:hover {
  border-color: #6366f1;
  color: #a5b4fc;
}

/* Viewport Dropdown Menu */
.viewport-menu {
  position: absolute;
  top: calc(100% + 8px);
  left: 0;
  min-width: 240px;
  background: #111827;
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: var(--radius-md, 8px);
  padding: 6px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  box-shadow: 0 12px 28px rgba(0, 0, 0, 0.5);
  z-index: 1000;
  animation: fadeIn 0.15s ease;
}

.menu-header {
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted, #94a3b8);
  padding: 6px 8px 4px;
}

.viewport-menu-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: var(--radius-sm, 6px);
  background: transparent;
  border: none;
  color: var(--text-secondary, #cbd5e1);
  text-align: left;
  cursor: pointer;
  transition: all 0.15s ease;
  width: 100%;
}

.viewport-menu-item:hover {
  background: rgba(255, 255, 255, 0.08);
  color: #ffffff;
}

.viewport-menu-item.active {
  background: rgba(99, 102, 241, 0.25);
  color: #ffffff;
  font-weight: 600;
}

.vp-icon {
  font-size: 15px;
}

.vp-meta {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.vp-name {
  font-size: 12px;
  line-height: 1.2;
}

.vp-aspect {
  font-size: 10px;
  color: var(--text-muted, #94a3b8);
  margin-top: 1px;
}

.vp-check {
  color: #818cf8;
  font-weight: bold;
}
</style>
