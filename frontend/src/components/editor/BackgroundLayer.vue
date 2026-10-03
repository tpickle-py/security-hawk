<script setup lang="ts">
import { computed } from "vue";
import type { BackgroundAsset } from "@/types/plan";
import { api } from "@/services/api";

const props = defineProps<{
  background: BackgroundAsset | null;
}>();

const assetUrl = computed(() => {
  if (!props.background?.url) return "";
  return api.resolveAssetUrl(props.background.url);
});
</script>

<template>
  <g class="background-layer" v-if="background">
    <image
      :href="assetUrl"
      :x="background.x"
      :y="background.y"
      :width="background.width"
      :height="background.height"
      :transform="background.rotation ? `rotate(${background.rotation}, ${background.x + background.width / 2}, ${background.y + background.height / 2})` : undefined"
      preserveAspectRatio="xMidYMid meet"
    />
  </g>
</template>

<style scoped>
.background-layer {
  pointer-events: none;
  user-select: none;
}
</style>
