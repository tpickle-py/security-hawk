<script setup lang="ts">
import { ref, computed } from "vue";
import { usePlanStore } from "@/stores/planStore";
import { useEntityStore } from "@/stores/entityStore";

const emit = defineEmits<{
  (e: "close"): void;
}>();

const planStore = usePlanStore();
const entityStore = useEntityStore();

// Grid dimensions
const maxGridCols = 8;
const maxGridRows = 8;
const hoveredCol = ref(0);
const hoveredRow = ref(0);
const selectedCols = ref(2);
const selectedRows = ref(2);

// Room sizing & placement
const roomWidth = ref(220);
const roomHeight = ref(170);
const namingPrefix = ref<"Room" | "Bedroom" | "Office" | "Closet" | "Storage" | "Zone" | "Custom">("Room");
const customPrefix = ref("");

// Mode: Architectural Rooms vs Sub-Areas (Closets / Zones)
const creationMode = ref<"rooms" | "subareas">("rooms");
const selectedParentAreaId = ref<string>("");
const createDividingWalls = ref(true);
const createDoorOpenings = ref(true);
const wallThickness = ref(8);

// Preset templates
interface GridPreset {
  name: string;
  icon: string;
  cols: number;
  rows: number;
  mode: "rooms" | "subareas";
  prefix: "Room" | "Bedroom" | "Office" | "Closet" | "Storage" | "Zone" | "Custom";
  customPrefix?: string;
  desc: string;
}

const presets: GridPreset[] = [
  {
    name: "2 × 2 Quad Rooms",
    icon: "🏠",
    cols: 2,
    rows: 2,
    mode: "rooms",
    prefix: "Room",
    desc: "4 standard rooms with perimeter and dividing partition walls",
  },
  {
    name: "1 × 3 Closets / Storage",
    icon: "🚪",
    cols: 3,
    rows: 1,
    mode: "subareas",
    prefix: "Closet",
    desc: "3 adjacent sub-area closets/storage subsections",
  },
  {
    name: "3 × 2 Wing / Suites",
    icon: "🏢",
    cols: 3,
    rows: 2,
    mode: "rooms",
    prefix: "Office",
    desc: "6 office suites / living units with doors",
  },
  {
    name: "2 × 1 Dual Zone Split",
    icon: "🔲",
    cols: 2,
    rows: 1,
    mode: "subareas",
    prefix: "Zone",
    desc: "Split area into Left & Right monitored subsections",
  },
];

function applyPreset(p: GridPreset) {
  selectedCols.value = p.cols;
  selectedRows.value = p.rows;
  creationMode.value = p.mode;
  namingPrefix.value = p.prefix;
  if (p.customPrefix) customPrefix.value = p.customPrefix;
}

function handleCellHover(r: number, c: number) {
  hoveredRow.value = r;
  hoveredCol.value = c;
}

function handleCellLeave() {
  hoveredRow.value = 0;
  hoveredCol.value = 0;
}

function handleCellClick(r: number, c: number) {
  selectedRows.value = r;
  selectedCols.value = c;
}

const activeDisplayCols = computed(() => {
  return hoveredCol.value > 0 ? hoveredCol.value : selectedCols.value;
});

const activeDisplayRows = computed(() => {
  return hoveredRow.value > 0 ? hoveredRow.value : selectedRows.value;
});

// Generated room names preview
const generatedNames = computed(() => {
  const names: string[] = [];
  const prefix = namingPrefix.value === "Custom" && customPrefix.value.trim()
    ? customPrefix.value.trim()
    : namingPrefix.value;

  const total = selectedCols.value * selectedRows.value;
  for (let i = 1; i <= total; i++) {
    names.push(`${prefix} ${i}`);
  }
  return names;
});

// Mini Preview SVG calculations
const previewSvgWidth = 320;
const previewSvgHeight = 180;

const previewScale = computed(() => {
  const totalW = selectedCols.value * roomWidth.value;
  const totalH = selectedRows.value * roomHeight.value;
  const pad = 30;
  const scaleX = (previewSvgWidth - pad) / totalW;
  const scaleY = (previewSvgHeight - pad) / totalH;
  return Math.min(scaleX, scaleY);
});

const previewOrigin = computed(() => {
  const totalW = selectedCols.value * roomWidth.value * previewScale.value;
  const totalH = selectedRows.value * roomHeight.value * previewScale.value;
  return {
    x: (previewSvgWidth - totalW) / 2,
    y: (previewSvgHeight - totalH) / 2,
  };
});

function handleInsertGrid() {
  // Determine startX and startY to center the grid on the floor plan
  let targetCenterX = 600;
  let targetCenterY = 450;

  const bg = planStore.currentFloor?.background;
  if (bg && bg.width > 0 && bg.height > 0) {
    targetCenterX = bg.x + bg.width / 2;
    targetCenterY = bg.y + bg.height / 2;
  }

  const totalWidth = selectedCols.value * roomWidth.value;
  const totalHeight = selectedRows.value * roomHeight.value;
  const startX = Math.round(targetCenterX - totalWidth / 2);
  const startY = Math.round(targetCenterY - totalHeight / 2);

  planStore.addRoomsGrid({
    cols: selectedCols.value,
    rows: selectedRows.value,
    startX,
    startY,
    roomWidth: roomWidth.value,
    roomHeight: roomHeight.value,
    names: generatedNames.value,
    asSubAreas: creationMode.value === "subareas",
    parentAreaId: selectedParentAreaId.value || null,
    createWalls: createDividingWalls.value,
    createDoors: createDoorOpenings.value,
    wallThickness: wallThickness.value,
  });

  emit("close");
}

const previewFontSize = computed(() => {
  const targetPx = selectedCols.value > 4 || selectedRows.value > 4 ? 11 : 13;
  return Math.max(10, Math.round(targetPx / (previewScale.value || 1)));
});

function getPreviewCellLabel(idx: number): string {
  if (selectedCols.value > 4 || selectedRows.value > 4) {
    const prefixChar = namingPrefix.value === "Custom" && customPrefix.value.trim()
      ? customPrefix.value.trim().substring(0, 1).toUpperCase()
      : (namingPrefix.value === "Bedroom" ? "BR" : namingPrefix.value.substring(0, 1));
    return `${prefixChar}${idx + 1}`;
  }
  return generatedNames.value[idx] || `Room ${idx + 1}`;
}
</script>

<template>
  <Teleport to="body">
    <div class="modal-backdrop" @click.self="emit('close')">
    <div class="modal-card glass-panel">
      <!-- Modal Header -->
      <div class="modal-header">
        <div class="title-with-icon">
          <span class="icon">▦</span>
          <div>
            <h3>Room & Subsection Grid Generator</h3>
            <p class="subtitle">Insert a structured grid of rooms or subdivide an existing area into subsections</p>
          </div>
        </div>
        <button class="close-btn" @click="emit('close')">✕</button>
      </div>

      <div class="modal-body">
        <!-- Quick Presets -->
        <div class="presets-row">
          <button
            v-for="p in presets"
            :key="p.name"
            class="preset-chip"
            @click="applyPreset(p)"
            :title="p.desc"
          >
            <span>{{ p.icon }}</span>
            <span>{{ p.name }}</span>
          </button>
        </div>

        <div class="grid-dialog-layout">
          <!-- Left Column: Interactive Table Picker & Dimension Controls -->
          <div class="left-col">
            <!-- Word-Style Interactive Table Picker -->
            <div class="table-picker-box">
              <div class="table-picker-header">
                <span class="picker-label">Table Grid Selector</span>
                <span class="grid-size-indicator">{{ activeDisplayCols }} × {{ activeDisplayRows }} {{ creationMode === 'subareas' ? 'Subsections' : 'Rooms' }}</span>
              </div>

              <div class="table-matrix" @mouseleave="handleCellLeave">
                <div v-for="r in maxGridRows" :key="`row-${r}`" class="matrix-row">
                  <div
                    v-for="c in maxGridCols"
                    :key="`cell-${r}-${c}`"
                    class="matrix-cell"
                    :class="{
                      highlighted: r <= activeDisplayRows && c <= activeDisplayCols,
                      selected: r <= selectedRows && c <= selectedCols && hoveredCol === 0
                    }"
                    @mouseenter="handleCellHover(r, c)"
                    @click="handleCellClick(r, c)"
                  ></div>
                </div>
              </div>
            </div>

            <!-- Spinbox Inputs for Exact Numbers -->
            <div class="controls-grid">
              <div class="control-field">
                <label>Columns</label>
                <div class="stepper">
                  <button @click="selectedCols = Math.max(1, selectedCols - 1)">−</button>
                  <input type="number" v-model.number="selectedCols" min="1" max="12" />
                  <button @click="selectedCols = Math.min(12, selectedCols + 1)">+</button>
                </div>
              </div>

              <div class="control-field">
                <label>Rows</label>
                <div class="stepper">
                  <button @click="selectedRows = Math.max(1, selectedRows - 1)">−</button>
                  <input type="number" v-model.number="selectedRows" min="1" max="12" />
                  <button @click="selectedRows = Math.min(12, selectedRows + 1)">+</button>
                </div>
              </div>

              <div class="control-field">
                <label>Cell Width (px)</label>
                <input type="number" v-model.number="roomWidth" step="10" min="60" max="800" class="input-text" />
              </div>

              <div class="control-field">
                <label>Cell Height (px)</label>
                <input type="number" v-model.number="roomHeight" step="10" min="60" max="800" class="input-text" />
              </div>
            </div>
          </div>

          <!-- Right Column: Settings & Live Preview -->
          <div class="right-col">
            <!-- Mode Toggle: Rooms vs Sub-Areas -->
            <div class="mode-toggle-group">
              <button
                class="mode-btn"
                :class="{ active: creationMode === 'rooms' }"
                @click="creationMode = 'rooms'"
              >
                <span>🏢 Full Rooms & Walls</span>
              </button>
              <button
                class="mode-btn"
                :class="{ active: creationMode === 'subareas' }"
                @click="creationMode = 'subareas'"
              >
                <span>📦 Sub-Areas (Closets / Zones)</span>
              </button>
            </div>

            <!-- Naming Template -->
            <div class="naming-section">
              <label>Naming Prefix</label>
              <div class="naming-pills">
                <button
                  v-for="pref in (creationMode === 'subareas' ? ['Closet', 'Storage', 'Zone', 'Custom'] : ['Room', 'Bedroom', 'Office', 'Custom'])"
                  :key="pref"
                  class="naming-pill"
                  :class="{ active: namingPrefix === pref }"
                  @click="namingPrefix = (pref as any)"
                >
                  {{ pref }}
                </button>
              </div>
              <input
                v-if="namingPrefix === 'Custom'"
                type="text"
                v-model="customPrefix"
                placeholder="Custom Prefix (e.g. Studio, Suite)..."
                class="input-text custom-prefix-input"
              />
            </div>

            <!-- Mode-Specific Options -->
            <div class="mode-options" v-if="creationMode === 'rooms'">
              <label class="checkbox-label">
                <input type="checkbox" v-model="createDividingWalls" />
                <span>Build Partition & Boundary Walls</span>
              </label>

              <label class="checkbox-label" v-if="createDividingWalls">
                <input type="checkbox" v-model="createDoorOpenings" />
                <span>Insert Standard Door Openings</span>
              </label>
            </div>

            <div class="mode-options" v-else-if="creationMode === 'subareas' && entityStore.areas.length > 0">
              <label class="field-label">Parent Area / Room (Optional)</label>
              <select v-model="selectedParentAreaId" class="select-field">
                <option value="">-- Standalone Sub-Areas --</option>
                <option v-for="a in entityStore.areas" :key="a.area_id" :value="a.area_id">
                  📍 {{ a.name }}
                </option>
              </select>
            </div>

            <!-- Live Mini Preview -->
            <div class="preview-card">
              <div class="preview-header">
                <span>Layout Preview ({{ selectedCols }}×{{ selectedRows }})</span>
                <span class="preview-dims">{{ selectedCols * roomWidth }} × {{ selectedRows * roomHeight }}px</span>
              </div>

              <svg :width="previewSvgWidth" :height="previewSvgHeight" class="preview-svg">
                <rect width="100%" height="100%" fill="rgba(0, 0, 0, 0.25)" rx="6" />

                <!-- Grid Cells -->
                <g :transform="`translate(${previewOrigin.x}, ${previewOrigin.y}) scale(${previewScale})`">
                  <g v-for="r in selectedRows" :key="`pr-${r}`">
                    <g v-for="c in selectedCols" :key="`pc-${r}-${c}`">
                      <rect
                        :x="(c - 1) * roomWidth"
                        :y="(r - 1) * roomHeight"
                        :width="roomWidth"
                        :height="roomHeight"
                        :fill="creationMode === 'subareas' ? 'rgba(16, 185, 129, 0.12)' : 'rgba(99, 102, 241, 0.14)'"
                        :stroke="creationMode === 'subareas' ? 'rgba(16, 185, 129, 0.6)' : 'rgba(99, 102, 241, 0.6)'"
                        :stroke-width="1.5"
                        :stroke-dasharray="creationMode === 'subareas' ? '4 3' : undefined"
                      />
                      <text
                        :x="(c - 1) * roomWidth + roomWidth / 2"
                        :y="(r - 1) * roomHeight + roomHeight / 2"
                        text-anchor="middle"
                        dominant-baseline="central"
                        fill="#ffffff"
                        :font-size="previewFontSize"
                        font-weight="bold"
                      >
                        {{ getPreviewCellLabel((r - 1) * selectedCols + (c - 1)) }}
                        <title>{{ generatedNames[(r - 1) * selectedCols + (c - 1)] }}</title>
                      </text>
                    </g>
                  </g>
                </g>
              </svg>
            </div>
          </div>
        </div>
      </div>

      <!-- Modal Footer -->
      <div class="modal-footer">
        <div class="footer-summary">
          Creates <strong>{{ selectedCols * selectedRows }}</strong> {{ creationMode === 'subareas' ? 'subsections' : 'rooms' }} centered on current floor plan.
        </div>
        <div class="footer-actions">
          <button class="btn-cancel" @click="emit('close')">Cancel</button>
          <button class="btn-submit" @click="handleInsertGrid">
            Insert {{ selectedCols * selectedRows }} {{ creationMode === 'subareas' ? 'Subsections' : 'Rooms' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</Teleport>
</template>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  padding: 20px;
}

.modal-card {
  width: 100%;
  max-width: 760px;
  max-height: 90vh;
  background: #111827;
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: var(--radius-lg, 12px);
  box-shadow: 0 24px 48px rgba(0, 0, 0, 0.6);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  animation: modalScale 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

.modal-body {
  padding: 18px 24px;
  overflow-y: auto;
  max-height: calc(90vh - 130px);
}

@keyframes modalScale {
  from {
    opacity: 0;
    transform: scale(0.95) translateY(12px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

.modal-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 18px 24px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.title-with-icon {
  display: flex;
  align-items: center;
  gap: 12px;
}

.title-with-icon .icon {
  font-size: 24px;
  color: var(--color-primary, #6366f1);
}

.modal-header h3 {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary, #ffffff);
  margin: 0;
}

.subtitle {
  font-size: 12px;
  color: var(--text-muted, #94a3b8);
  margin: 3px 0 0;
}

.close-btn {
  background: transparent;
  border: none;
  color: var(--text-muted, #94a3b8);
  font-size: 16px;
  cursor: pointer;
  padding: 4px;
  border-radius: var(--radius-sm);
}

.close-btn:hover {
  color: #ffffff;
  background: rgba(255, 255, 255, 0.1);
}

.modal-body {
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
  gap: 18px;
  max-height: 75vh;
  overflow-y: auto;
}

/* Presets row */
.presets-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.preset-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: var(--radius-sm, 6px);
  padding: 5px 10px;
  font-size: 11px;
  color: var(--text-secondary, #cbd5e1);
  cursor: pointer;
  transition: all 0.15s ease;
}

.preset-chip:hover {
  background: rgba(99, 102, 241, 0.2);
  border-color: #6366f1;
  color: #ffffff;
}

.grid-dialog-layout {
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: 24px;
}

/* Table Matrix Picker */
.table-picker-box {
  background: rgba(0, 0, 0, 0.25);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: var(--radius-md, 8px);
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.table-picker-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.picker-label {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-secondary);
}

.grid-size-indicator {
  font-size: 12px;
  font-weight: 700;
  color: #818cf8;
}

.table-matrix {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 4px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: var(--radius-sm, 6px);
}

.matrix-row {
  display: flex;
  gap: 4px;
}

.matrix-cell {
  width: 24px;
  height: 24px;
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 3px;
  background: rgba(255, 255, 255, 0.03);
  cursor: pointer;
  transition: all 0.1s ease;
}

.matrix-cell.highlighted {
  background: rgba(99, 102, 241, 0.5);
  border-color: #818cf8;
}

.matrix-cell.selected {
  background: rgba(99, 102, 241, 0.35);
  border-color: #6366f1;
}

/* Controls Grid */
.controls-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-top: 14px;
}

.control-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.control-field label {
  font-size: 11px;
  color: var(--text-muted, #94a3b8);
  font-weight: 500;
}

.stepper {
  display: flex;
  align-items: center;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: var(--radius-sm, 6px);
  overflow: hidden;
}

.stepper button {
  width: 28px;
  height: 28px;
  background: transparent;
  border: none;
  color: var(--text-primary);
  font-size: 14px;
  font-weight: bold;
  cursor: pointer;
}

.stepper button:hover {
  background: rgba(255, 255, 255, 0.1);
}

.stepper input {
  flex: 1;
  width: 32px;
  background: transparent;
  border: none;
  color: #ffffff;
  text-align: center;
  font-size: 12px;
  font-weight: 600;
}

.input-text {
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: var(--radius-sm, 6px);
  padding: 6px 10px;
  color: #ffffff;
  font-size: 12px;
}

/* Right column styles */
.right-col {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.mode-toggle-group {
  display: flex;
  background: rgba(0, 0, 0, 0.3);
  padding: 3px;
  border-radius: var(--radius-sm, 6px);
  gap: 4px;
}

.mode-btn {
  flex: 1;
  padding: 6px 12px;
  background: transparent;
  border: none;
  color: var(--text-muted, #94a3b8);
  font-size: 12px;
  font-weight: 600;
  border-radius: var(--radius-sm, 4px);
  cursor: pointer;
  transition: all 0.15s ease;
}

.mode-btn.active {
  background: var(--color-primary, #6366f1);
  color: #ffffff;
}

.naming-section {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.naming-section label,
.field-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted, #94a3b8);
}

.naming-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.naming-pill {
  padding: 4px 10px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: var(--radius-sm, 6px);
  color: var(--text-secondary);
  font-size: 11px;
  cursor: pointer;
}

.naming-pill.active {
  background: rgba(99, 102, 241, 0.25);
  border-color: #6366f1;
  color: #ffffff;
  font-weight: 600;
}

.custom-prefix-input {
  margin-top: 4px;
}

.mode-options {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--text-primary);
  cursor: pointer;
}

.checkbox-label input {
  accent-color: var(--color-primary, #6366f1);
}

.select-field {
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: var(--radius-sm, 6px);
  padding: 6px 10px;
  color: #ffffff;
  font-size: 12px;
}

/* Preview Card */
.preview-card {
  display: flex;
  flex-direction: column;
  gap: 6px;
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: var(--radius-md, 8px);
  padding: 10px;
}

.preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 11px;
  color: var(--text-muted, #94a3b8);
  font-weight: 600;
}

.preview-svg {
  width: 100%;
  height: 180px;
  border-radius: var(--radius-sm, 6px);
  overflow: hidden;
}

/* Modal Footer */
.modal-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(0, 0, 0, 0.2);
}

.footer-summary {
  font-size: 12px;
  color: var(--text-secondary, #cbd5e1);
}

.footer-summary strong {
  color: #818cf8;
}

.footer-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.btn-cancel {
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.15);
  color: var(--text-secondary);
  padding: 7px 14px;
  border-radius: var(--radius-sm, 6px);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
}

.btn-cancel:hover {
  background: rgba(255, 255, 255, 0.06);
  color: #ffffff;
}

.btn-submit {
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

.btn-submit:hover {
  background: #4f46e5;
  box-shadow: 0 0 12px rgba(99, 102, 241, 0.4);
}
</style>
