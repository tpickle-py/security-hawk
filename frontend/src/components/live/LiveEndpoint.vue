<script setup lang="ts">
import { computed } from "vue";
import type { Endpoint } from "@/types/plan";
import { useLiveStore } from "@/stores/liveStore";

const props = defineProps<{
  endpoint: Endpoint;
}>();

const emit = defineEmits<{
  (e: "click-camera", endpoint: Endpoint): void;
}>();

const liveStore = useLiveStore();

const entityState = computed(() => {
  return liveStore.getState(props.endpoint.entity_id);
});

const isUnavailable = computed(() => {
  const st = entityState.value?.state;
  return st === "unavailable" || st === "unknown" || st === undefined;
});

const isActive = computed(() => {
  const st = entityState.value?.state?.toLowerCase();
  return st === "on" || st === "detected" || st === "open";
});

// Check companion states
const hasActiveCompanion = computed(() => {
  if (!props.endpoint.companions || props.endpoint.companions.length === 0) return false;
  return props.endpoint.companions.some((compEid) => {
    const compState = liveStore.getState(compEid)?.state?.toLowerCase();
    return compState === "on" || compState === "detected" || compState === "open";
  });
});

const iconHref = computed(() => {
  if (props.endpoint.type === "motion") {
    return isActive.value ? "#icon-motion-active" : "#icon-motion-clear";
  }
  if (props.endpoint.type === "door") {
    return isActive.value ? "#icon-door-open" : "#icon-door-closed";
  }
  if (props.endpoint.type === "window") {
    return isActive.value ? "#icon-window-open" : "#icon-window-closed";
  }
  if (props.endpoint.type === "camera") {
    return "#icon-camera";
  }
  return "#icon-generic";
});

function handleClick() {
  if (props.endpoint.type === "camera") {
    emit("click-camera", props.endpoint);
  }
}
</script>

<template>
  <g
    class="live-endpoint"
    :class="{
      active: isActive,
      unavailable: isUnavailable,
      'is-camera': endpoint.type === 'camera',
    }"
    :transform="`translate(${endpoint.x}, ${endpoint.y}) rotate(${endpoint.rotation || 0})`"
    :tabindex="0"
    role="button"
    :aria-label="`${endpoint.label || endpoint.entity_id} (${endpoint.type})`"
    @click="handleClick"
    @keydown.enter.prevent="handleClick"
    @keydown.space.prevent="handleClick"
  >
    <!-- Focus ring for remote and keyboard navigation -->
    <circle
      cx="0"
      cy="0"
      r="25"
      class="remote-focus-ring"
      fill="none"
    />

    <!-- Motion pulse wave animation if active -->
    <circle
      v-if="endpoint.type === 'motion' && isActive"
      cx="0"
      cy="0"
      r="28"
      class="motion-wave animate-pulse-glow"
      fill="rgba(239, 68, 68, 0.15)"
      stroke="rgba(239, 68, 68, 0.5)"
      stroke-width="1.5"
    />

    <!-- Door / Window open warning glow ring -->
    <circle
      v-if="(endpoint.type === 'door' || endpoint.type === 'window') && isActive"
      cx="0"
      cy="0"
      r="28"
      class="motion-wave animate-pulse-glow"
      fill="rgba(245, 158, 11, 0.15)"
      stroke="rgba(245, 158, 11, 0.6)"
      stroke-width="1.5"
    />

    <!-- Icon -->
    <use :href="iconHref" />

    <!-- Group unit badge -->
    <g v-if="endpoint.group_name || endpoint.group_id" transform="translate(12, 12)">
      <circle cx="0" cy="0" r="6" fill="#6366f1" stroke="#ffffff" stroke-width="1" />
      <text x="0" y="0" text-anchor="middle" dominant-baseline="central" fill="#ffffff" font-size="7" font-weight="bold">G</text>
    </g>

    <!-- Companion badge -->
    <circle
      v-if="hasActiveCompanion"
      cx="12"
      cy="-12"
      r="5"
      fill="#f59e0b"
      stroke="#ffffff"
      stroke-width="1.5"
      class="animate-pulse-glow"
    />

    <!-- Unavailable indicator -->
    <g v-if="isUnavailable" transform="translate(10, -10)">
      <circle cx="0" cy="0" r="6" fill="#64748b" />
      <text x="0" y="0" text-anchor="middle" dominant-baseline="central" fill="#ffffff" font-size="8" font-weight="bold">?</text>
    </g>

    <!-- Label -->
    <text
      y="28"
      text-anchor="middle"
      class="endpoint-label"
      :class="{ 'label-active': isActive }"
      :transform="endpoint.rotation ? `rotate(${-endpoint.rotation})` : undefined"
    >
      {{ endpoint.label || endpoint.entity_id.split('.')[1] }}
    </text>
  </g>
</template>

<style scoped>
.live-endpoint {
  user-select: none;
  transition: all 0.2s ease-out;
  cursor: pointer;
  outline: none;
}

.remote-focus-ring {
  stroke: transparent;
  stroke-width: 2.5px;
  stroke-dasharray: 4 2;
  transition: all 0.15s ease-in-out;
}

.live-endpoint:focus-visible .remote-focus-ring,
.live-endpoint:focus .remote-focus-ring {
  stroke: #6366f1;
  fill: rgba(99, 102, 241, 0.25);
  filter: drop-shadow(0 0 12px #6366f1);
  stroke-dasharray: none;
}

.live-endpoint:focus-visible .endpoint-label,
.live-endpoint:focus .endpoint-label {
  fill: #ffffff;
  font-weight: 700;
  text-shadow: 0 0 8px #6366f1;
}

.is-camera {
  cursor: pointer;
}

.is-camera:hover {
  filter: drop-shadow(0 0 8px var(--accent-primary-glow));
}

.unavailable {
  opacity: 0.5;
  filter: grayscale(0.8);
}

.endpoint-label {
  fill: var(--text-secondary);
  font-size: 11px;
  font-weight: 500;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.8), 0 0 6px rgba(0, 0, 0, 0.9);
  pointer-events: none;
  transition: fill 0.2s ease;
}

.label-active {
  fill: #ffffff;
  font-weight: 600;
}
</style>
