<script setup lang="ts">
import { computed } from "vue";
import type { Endpoint } from "@/types/plan";

const props = defineProps<{
  endpoint: Endpoint;
  isSelected?: boolean;
}>();

const coverageAngle = computed(() => {
  return (
    props.endpoint.coverage?.angle ??
    (props.endpoint as any).fov_beam_angle ??
    (props.endpoint.type === "camera" ? 70 : 85)
  );
});

const coverageRange = computed(() => {
  return (
    props.endpoint.coverage?.range ??
    (props.endpoint as any).fov_depth_px ??
    (props.endpoint.type === "camera" ? 120 : 80)
  );
});

const hasCoverage = computed(() => {
  return (
    Boolean(props.endpoint.coverage) ||
    props.endpoint.type === "camera" ||
    props.endpoint.type === "motion" ||
    Boolean((props.endpoint as any).fov_beam_angle)
  );
});

const coveragePath = computed(() => {
  if (!hasCoverage.value) return null;
  const range = coverageRange.value;
  const angleDeg = coverageAngle.value;
  const halfRad = (angleDeg / 2) * (Math.PI / 180);
  const x1 = range * Math.cos(-halfRad);
  const y1 = range * Math.sin(-halfRad);
  const x2 = range * Math.cos(halfRad);
  const y2 = range * Math.sin(halfRad);
  const largeArcFlag = angleDeg > 180 ? 1 : 0;
  return `M 0 0 L ${x1} ${y1} A ${range} ${range} 0 ${largeArcFlag} 1 ${x2} ${y2} Z`;
});
</script>

<template>
  <g
    v-if="coveragePath"
    class="editor-coverage-group"
    pointer-events="none"
    :transform="`translate(${endpoint.x}, ${endpoint.y}) rotate(${endpoint.rotation || 0})`"
  >
    <path
      :d="coveragePath"
      :fill="
        endpoint.type === 'camera'
          ? isSelected
            ? 'rgba(99, 102, 241, 0.18)'
            : 'rgba(99, 102, 241, 0.09)'
          : isSelected
          ? 'rgba(16, 185, 129, 0.18)'
          : 'rgba(16, 185, 129, 0.09)'
      "
      :stroke="
        endpoint.type === 'camera'
          ? isSelected
            ? '#818cf8'
            : 'rgba(99, 102, 241, 0.45)'
          : isSelected
          ? '#34d399'
          : 'rgba(16, 185, 129, 0.45)'
      "
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
      :stroke="
        endpoint.type === 'camera'
          ? isSelected
            ? '#a5b4fc'
            : 'rgba(99, 102, 241, 0.4)'
          : isSelected
          ? '#6ee7b7'
          : 'rgba(16, 185, 129, 0.4)'
      "
      stroke-width="1.2"
      stroke-dasharray="2 2"
    />
    <!-- Aiming pointer tip -->
    <polygon
      :points="`${coverageRange},0 ${coverageRange - 8},-4 ${coverageRange - 8},4`"
      :fill="
        endpoint.type === 'camera'
          ? isSelected
            ? '#818cf8'
            : 'rgba(99, 102, 241, 0.6)'
          : isSelected
          ? '#34d399'
          : 'rgba(16, 185, 129, 0.6)'
      "
    />
  </g>
</template>

<style scoped>
.editor-coverage-group {
  pointer-events: none;
}
.editor-coverage-cone {
  pointer-events: none;
  transition: all 0.2s ease-out;
}
</style>
