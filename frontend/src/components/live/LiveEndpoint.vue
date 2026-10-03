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
  if (props.endpoint.type === "composite") {
    return isActive.value ? "#icon-composite-active" : "#icon-composite-clear";
  }
  return "#icon-generic";
});

// Coverage Cone Math (Camera FOV / Motion PIR Sector)
const coveragePath = computed(() => {
  if (props.endpoint.type !== "camera" && props.endpoint.type !== "motion") return null;

  const range = props.endpoint.coverage?.range || (props.endpoint.type === "camera" ? 110 : 75);
  const angleDeg = props.endpoint.coverage?.angle || (props.endpoint.type === "camera" ? 70 : 85);

  const halfRad = (angleDeg / 2) * (Math.PI / 180);
  const x1 = range * Math.cos(-halfRad);
  const y1 = range * Math.sin(-halfRad);
  const x2 = range * Math.cos(halfRad);
  const y2 = range * Math.sin(halfRad);
  const largeArcFlag = angleDeg > 180 ? 1 : 0;

  return `M 0 0 L ${x1} ${y1} A ${range} ${range} 0 ${largeArcFlag} 1 ${x2} ${y2} Z`;
});

// Stale RF Sensor Check
const isStale = computed(() => {
  if (!props.endpoint.stale_after) return false;
  const lastChangedStr = entityState.value?.last_changed;
  if (!lastChangedStr) return false;

  const lastChangedTime = new Date(lastChangedStr).getTime();
  const now = Date.now();
  let maxAgeSec = 24 * 3600; // default 24h

  const sa = props.endpoint.stale_after.trim().toLowerCase();
  if (sa.endsWith("h")) {
    maxAgeSec = parseFloat(sa) * 3600;
  } else if (sa.endsWith("m")) {
    maxAgeSec = parseFloat(sa) * 60;
  } else if (sa.endsWith("d")) {
    maxAgeSec = parseFloat(sa) * 86400;
  } else if (!isNaN(parseFloat(sa))) {
    maxAgeSec = parseFloat(sa);
  }

  return (now - lastChangedTime) / 1000 > maxAgeSec;
});

const isHighlighted = computed(() => {
  return liveStore.highlightedEndpointId === props.endpoint.id;
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
      'is-highlighted': isHighlighted,
    }"
    :transform="`translate(${endpoint.x}, ${endpoint.y}) rotate(${endpoint.rotation || 0})`"
    :tabindex="0"
    role="button"
    :aria-label="`${endpoint.label || endpoint.entity_id} (${endpoint.type})`"
    @click="handleClick"
    @keydown.enter.prevent="handleClick"
    @keydown.space.prevent="handleClick"
  >
    <!-- Coverage Cone (Field of View / Detection Sector) -->
    <path
      v-if="coveragePath"
      :d="coveragePath"
      :fill="endpoint.type === 'camera' ? 'rgba(99, 102, 241, 0.10)' : isActive ? 'rgba(239, 68, 68, 0.22)' : 'rgba(16, 185, 129, 0.08)'"
      :stroke="endpoint.type === 'camera' ? 'rgba(99, 102, 241, 0.35)' : isActive ? 'rgba(239, 68, 68, 0.65)' : 'rgba(16, 185, 129, 0.25)'"
      stroke-width="1.2"
      stroke-dasharray="3 3"
      class="coverage-cone"
    />

    <!-- Highlight Beacon Wave -->
    <circle
      v-if="isHighlighted"
      cx="0"
      cy="0"
      r="36"
      fill="rgba(99, 102, 241, 0.2)"
      stroke="#6366f1"
      stroke-width="2.5"
      class="beacon-pulse"
    />

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

    <!-- Composite rule active pulse ring -->
    <circle
      v-if="endpoint.type === 'composite' && isActive"
      cx="0"
      cy="0"
      r="30"
      class="motion-wave animate-pulse-glow"
      fill="rgba(168, 85, 247, 0.2)"
      stroke="rgba(239, 68, 68, 0.8)"
      stroke-width="2"
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

    <!-- Stale RF Sensor Warning Indicator -->
    <g v-if="isStale" transform="translate(-10, -10)">
      <circle cx="0" cy="0" r="7" fill="#f59e0b" stroke="#ffffff" stroke-width="1" />
      <text x="0" y="0" text-anchor="middle" dominant-baseline="central" fill="#ffffff" font-size="8" font-weight="bold">!</text>
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

.coverage-cone {
  pointer-events: none;
  transition: all 0.3s ease;
}

.beacon-pulse {
  animation: beaconWave 1.4s ease-out infinite;
  pointer-events: none;
}

@keyframes beaconWave {
  0% {
    r: 16;
    opacity: 0.9;
  }
  100% {
    r: 44;
    opacity: 0;
  }
}
</style>
