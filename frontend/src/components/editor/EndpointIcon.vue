<script setup lang="ts">
import { computed } from "vue";
import type { Endpoint } from "@/types/plan";

const props = defineProps<{
  endpoint: Endpoint;
  isSelected: boolean;
}>();

const emit = defineEmits<{
  (e: "select", endpoint: Endpoint, event: MouseEvent): void;
  (e: "drag-start", endpoint: Endpoint, event: MouseEvent): void;
}>();

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
