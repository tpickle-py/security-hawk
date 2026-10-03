<script setup lang="ts">
import { ref, computed } from "vue";
import { useEditorStore } from "@/stores/editorStore";
import { usePlanStore } from "@/stores/planStore";

const editorStore = useEditorStore();
const planStore = usePlanStore();

const distanceInput = ref<number>(5.0);

const pt1 = computed(() => editorStore.scalePoint1);
const pt2 = computed(() => editorStore.scalePoint2);

const pixelDistance = computed(() => {
  if (!pt1.value || !pt2.value) return 0;
  const dx = pt2.value.x - pt1.value.x;
  const dy = pt2.value.y - pt1.value.y;
  return Math.sqrt(dx * dx + dy * dy);
});

const canSave = computed(() => {
  return pt1.value && pt2.value && distanceInput.value > 0;
});

function applyScale() {
  if (!canSave.value || !pt1.value || !pt2.value) return;

  planStore.setScale({
    point1: { ...pt1.value },
    point2: { ...pt2.value },
    real_distance_m: Number(distanceInput.value),
  });

  editorStore.cancelScaleCalibration();
}
</script>

<template>
  <!-- SVG overlay line and points -->
  <g class="scale-svg-overlay" v-if="editorStore.isSettingScale">
    <line
      v-if="pt1 && pt2"
      :x1="pt1.x"
      :y1="pt1.y"
      :x2="pt2.x"
      :y2="pt2.y"
      stroke="#6366f1"
      stroke-width="2"
      stroke-dasharray="6 3"
    />
    <circle v-if="pt1" :cx="pt1.x" :cy="pt1.y" r="6" fill="#6366f1" stroke="#ffffff" stroke-width="2" />
    <circle v-if="pt2" :cx="pt2.x" :cy="pt2.y" r="6" fill="#10b981" stroke="#ffffff" stroke-width="2" />
  </g>

  <!-- HTML floating calibration dialog -->
  <div v-if="editorStore.isSettingScale && pt1 && pt2" class="scale-modal-wrapper">
    <div class="scale-dialog glass-panel">
      <div class="dialog-title">Set Scale Calibration</div>
      <div class="dialog-desc">
        Selected distance on canvas: <strong>{{ Math.round(pixelDistance) }} px</strong>.
        Enter the actual distance in metres between these two points:
      </div>

      <div class="input-row">
        <input
          type="number"
          v-model.number="distanceInput"
          step="0.1"
          min="0.1"
          placeholder="5.0"
          autofocus
          @keyup.enter="applyScale"
        />
        <span class="unit">metres</span>
      </div>

      <div class="dialog-actions">
        <button class="btn-secondary" @click="editorStore.cancelScaleCalibration">Cancel</button>
        <button class="btn-primary" :disabled="!canSave" @click="applyScale">Apply Scale</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.scale-svg-overlay {
  pointer-events: none;
}

.scale-modal-wrapper {
  position: absolute;
  top: 80px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 500;
  pointer-events: auto;
}

.scale-dialog {
  padding: 20px;
  width: 340px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.dialog-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

.dialog-desc {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.4;
}

.input-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.input-row input {
  flex: 1;
  font-size: 16px;
  padding: 8px 12px;
}

.unit {
  font-size: 14px;
  color: var(--text-muted);
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 6px;
}

.btn-secondary {
  padding: 8px 14px;
  background: var(--bg-surface);
  color: var(--text-secondary);
  border-radius: var(--radius-sm);
  font-size: 13px;
}

.btn-secondary:hover {
  color: var(--text-primary);
  background: var(--bg-secondary);
}

.btn-primary {
  padding: 8px 16px;
  background: var(--accent-primary);
  color: #ffffff;
  border-radius: var(--radius-sm);
  font-size: 13px;
  font-weight: 500;
}

.btn-primary:hover:not(:disabled) {
  background: var(--accent-primary-hover);
  box-shadow: 0 0 12px var(--accent-primary-glow);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
