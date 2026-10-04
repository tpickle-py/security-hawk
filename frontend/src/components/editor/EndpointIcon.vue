<script setup lang="ts">
import { computed } from "vue";
import type { Endpoint } from "@/types/plan";

const props = withDefaults(
  defineProps<{
    endpoint: Endpoint;
    isSelected: boolean;
    isOrphaned?: boolean;
  }>(),
  {
    isOrphaned: false,
  }
);

const emit = defineEmits<{
  (e: "select", endpoint: Endpoint, event: MouseEvent): void;
  (e: "drag-start", endpoint: Endpoint, event: MouseEvent): void;
}>();

const coveragePath = computed(() => {
  if (props.endpoint.type !== "camera" && !props.endpoint.coverage) return null;
  const range = props.endpoint.coverage?.range || (props.endpoint.type === "camera" ? 120 : 75);
  const angleDeg = props.endpoint.coverage?.angle || (props.endpoint.type === "camera" ? 70 : 85);
  const halfRad = (angleDeg / 2) * (Math.PI / 180);
  const x1 = range * Math.cos(-halfRad);
  const y1 = range * Math.sin(-halfRad);
  const x2 = range * Math.cos(halfRad);
  const y2 = range * Math.sin(halfRad);
  const largeArcFlag = angleDeg > 180 ? 1 : 0;
  return `M 0 0 L ${x1} ${y1} A ${range} ${range} 0 ${largeArcFlag} 1 ${x2} ${y2} Z`;
});

const coverageRange = computed(() => {
  return props.endpoint.coverage?.range || (props.endpoint.type === "camera" ? 120 : 75);
});

const iconHref = computed(() => {
  switch (props.endpoint.type) {
    case "motion":
      return "#icon-motion-clear";
    case "door":
      return "#icon-door-closed";
    case "window":
      return "#icon-window-closed";
    case "camera":
      return "#icon-camera";
    case "composite":
      return "#icon-composite-clear";
    default:
      return "#icon-generic";
  }
});

function handleMouseDown(e: MouseEvent) {
  emit("select", props.endpoint, e);
  emit("drag-start", props.endpoint, e);
}
</script>

<template>
  <g
    class="endpoint-icon-group"
    :class="{ selected: isSelected, grouped: Boolean(endpoint.group_id) }"
    :transform="`translate(${endpoint.x}, ${endpoint.y}) rotate(${endpoint.rotation || 0})`"
    @mousedown.stop="handleMouseDown"
  >
    <!-- Coverage FOV preview in editor -->
    <g v-if="coveragePath" class="editor-coverage-group">
      <path
        :d="coveragePath"
        :fill="endpoint.type === 'camera' ? (isSelected ? 'rgba(99, 102, 241, 0.18)' : 'rgba(99, 102, 241, 0.09)') : 'rgba(16, 185, 129, 0.09)'"
        :stroke="endpoint.type === 'camera' ? (isSelected ? '#818cf8' : 'rgba(99, 102, 241, 0.45)') : 'rgba(16, 185, 129, 0.45)'"
        :stroke-width="isSelected ? 1.8 : 1.2"
        stroke-dasharray="3 3"
        class="editor-coverage-cone"
      />
      <!-- Directional Aiming Vector (Center axis line & arrow tip) -->
      <line
        x1="0"
        y1="0"
        :x2="coverageRange"
        y2="0"
        :stroke="endpoint.type === 'camera' ? (isSelected ? '#a5b4fc' : 'rgba(99, 102, 241, 0.4)') : 'rgba(16, 185, 129, 0.4)'"
        stroke-width="1.2"
        stroke-dasharray="2 2"
      />
      <!-- Aiming pointer tip -->
      <polygon
        :points="`${coverageRange},0 ${coverageRange - 8},-4 ${coverageRange - 8},4`"
        :fill="endpoint.type === 'camera' ? (isSelected ? '#818cf8' : 'rgba(99, 102, 241, 0.6)') : 'rgba(16, 185, 129, 0.6)'"
      />
    </g>

    <!-- Selection highlight circle -->
    <circle
      v-if="isSelected"
      cx="0"
      cy="0"
      r="25"
      fill="rgba(99, 102, 241, 0.2)"
      stroke="#6366f1"
      stroke-width="2.5"
      stroke-dasharray="4 2"
    />

    <!-- Icon reference -->
    <use :href="iconHref" />

    <!-- Group unit badge -->
    <g v-if="endpoint.group_name || endpoint.group_id" transform="translate(11, -12)">
      <circle cx="0" cy="0" r="7" fill="#6366f1" stroke="#ffffff" stroke-width="1.5" />
      <text x="0" y="0" text-anchor="middle" dominant-baseline="central" fill="#ffffff" font-size="8" font-weight="bold">G</text>
    </g>

    <!-- Nested entity indicator -->
    <g v-if="endpoint.parent_id" transform="translate(-11, -12)">
      <circle cx="0" cy="0" r="5" fill="#f59e0b" stroke="#ffffff" stroke-width="1" />
    </g>

    <!-- Companion sensors badge indicator -->
    <g v-if="endpoint.companions && endpoint.companions.length > 0" transform="translate(-12, 10)">
      <circle cx="0" cy="0" r="5.5" fill="#10b981" stroke="#ffffff" stroke-width="1" />
      <text x="0" y="0" text-anchor="middle" dominant-baseline="central" fill="#ffffff" font-size="7" font-weight="bold">{{ endpoint.companions.length }}</text>
    </g>

    <!-- Linked cameras badge indicator -->
    <g v-if="endpoint.cameras && endpoint.cameras.length > 0" transform="translate(12, 10)">
      <circle cx="0" cy="0" r="5.5" fill="#3b82f6" stroke="#ffffff" stroke-width="1" />
      <text x="0" y="0.5" text-anchor="middle" dominant-baseline="central" fill="#ffffff" font-size="7" font-weight="bold">C</text>
    </g>

    <!-- Orphaned / missing Home Assistant entity warning -->
    <g v-if="isOrphaned" transform="translate(0, -18)">
      <circle cx="0" cy="0" r="7" fill="#ef4444" stroke="#ffffff" stroke-width="1.5" />
      <text x="0" y="0" text-anchor="middle" dominant-baseline="central" fill="#ffffff" font-size="9" font-weight="bold">!</text>
    </g>

    <!-- Label -->
    <text
      y="28"
      text-anchor="middle"
      class="endpoint-label"
      :transform="endpoint.rotation ? `rotate(${-endpoint.rotation})` : undefined"
    >
      {{ endpoint.label || endpoint.entity_id.split('.')[1] }}
    </text>
  </g>
</template>

<style scoped>
.endpoint-icon-group {
  cursor: grab;
  user-select: none;
  transition: transform 0.05s ease-out;
}

.endpoint-icon-group:active {
  cursor: grabbing;
}

.endpoint-label {
  fill: var(--text-primary);
  font-size: 11px;
  font-weight: 500;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.8), 0 0 6px rgba(0, 0, 0, 0.9);
  pointer-events: none;
}

.endpoint-icon-group:hover circle:not([stroke]) {
  filter: drop-shadow(0 0 6px var(--accent-primary-glow));
}
</style>
