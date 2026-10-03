<script setup lang="ts">
import { useLiveStore } from "@/stores/liveStore";

const liveStore = useLiveStore();
</script>

<template>
  <Transition name="fade">
    <div v-if="!liveStore.isConnected" class="connection-banner">
      <div class="banner-content">
        <span class="status-indicator"></span>
        <span class="status-text">Disconnected from Home Assistant — Auto-reconnecting...</span>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.connection-banner {
  position: absolute;
  top: 16px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 1000;
  pointer-events: none;
}

.banner-content {
  display: flex;
  align-items: center;
  gap: 10px;
  background: rgba(239, 68, 68, 0.9);
  backdrop-filter: blur(8px);
  color: #ffffff;
  padding: 8px 18px;
  border-radius: var(--radius-full);
  font-size: 13px;
  font-weight: 500;
  box-shadow: 0 4px 12px rgba(239, 68, 68, 0.35);
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.status-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: #ffffff;
  animation: pulse-glow 1.5s infinite;
}
</style>
