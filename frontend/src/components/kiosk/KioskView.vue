<script setup lang="ts">
import { onMounted, onUnmounted, ref } from "vue";
import { useRoute } from "vue-router";
import { usePlanStore } from "@/stores/planStore";
import { useWebSocket } from "@/composables/useWebSocket";
import { api } from "@/services/api";

import LiveCanvas from "@/components/live/LiveCanvas.vue";
import ConnectionBanner from "@/components/shared/ConnectionBanner.vue";

const route = useRoute();
const planStore = usePlanStore();

const isReady = ref(false);
const errorMsg = ref<string | null>(null);

// WebSocket connection for live state updates
useWebSocket(() => planStore.currentPlanId);

let quietReturnTimer: number | null = null;
const quietReturnSeconds = 120; // Default quiet return

function resetQuietTimer() {
  if (quietReturnTimer) clearTimeout(quietReturnTimer);
  quietReturnTimer = window.setTimeout(() => {
    // Return to overview
    planStore.selectOverview();
  }, quietReturnSeconds * 1000);
}

function handleUserActivity() {
  resetQuietTimer();
}

onMounted(async () => {
  try {
    // Determine plan to load
    let planId = route.params.planId as string;
    if (!planId) {
      const list = await api.listPlans();
      if (list.plans.length > 0) {
        planId = list.plans[0].id;
      } else {
        const created = await api.createPlan("Default Plan");
        planId = created.id;
      }
    }

    await planStore.loadPlan(planId);
    isReady.value = true;
    resetQuietTimer();

    window.addEventListener("pointerdown", handleUserActivity);
    window.addEventListener("wheel", handleUserActivity);
  } catch (err: any) {
    errorMsg.value = err.message || "Failed to load kiosk view";
  }
});

onUnmounted(() => {
  if (quietReturnTimer) clearTimeout(quietReturnTimer);
  window.removeEventListener("pointerdown", handleUserActivity);
  window.removeEventListener("wheel", handleUserActivity);
});
</script>

<template>
  <div class="kiosk-container">
    <ConnectionBanner />

    <div v-if="errorMsg" class="kiosk-error">
      <h2>Security Hawk</h2>
      <p>{{ errorMsg }}</p>
    </div>

    <div v-else-if="!isReady" class="kiosk-loading">
      <div class="loading-spinner"></div>
      <p>Loading security floor plan...</p>
    </div>

    <div v-else class="kiosk-view">
      <LiveCanvas />

      <!-- Minimal clean overlay for TV navigation -->
      <div class="kiosk-status-pill glass-panel">
        <span class="hawk-badge">HAWK</span>
        <span class="floor-title">{{ planStore.isOverview ? 'Site Overview' : (planStore.currentFloor?.name || 'Floor') }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.kiosk-container {
  width: 100vw;
  height: 100vh;
  position: relative;
  overflow: hidden;
  background-color: var(--bg-primary);
}

.kiosk-view {
  width: 100%;
  height: 100%;
  position: relative;
}

.kiosk-status-pill {
  position: absolute;
  bottom: 24px;
  right: 24px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 16px;
  pointer-events: none;
  font-size: 13px;
  font-weight: 500;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
}

.hawk-badge {
  font-size: 10px;
  font-weight: 700;
  background: var(--accent-primary);
  color: #ffffff;
  padding: 2px 6px;
  border-radius: var(--radius-sm);
  letter-spacing: 1px;
}

.floor-title {
  color: var(--text-primary);
}

.kiosk-loading,
.kiosk-error {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  color: var(--text-secondary);
}

.loading-spinner {
  width: 36px;
  height: 36px;
  border: 3px solid rgba(255, 255, 255, 0.1);
  border-top-color: var(--accent-primary);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
