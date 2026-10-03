<script setup lang="ts">
import { ref, onMounted } from "vue";
import { usePlanStore } from "@/stores/planStore";
import { useEditorStore } from "@/stores/editorStore";
import { useLiveStore } from "@/stores/liveStore";
import { useWebSocket } from "@/composables/useWebSocket";
import { api } from "@/services/api";

import EditorCanvas from "@/components/editor/EditorCanvas.vue";
import LiveCanvas from "@/components/live/LiveCanvas.vue";
import EntityPicker from "@/components/editor/EntityPicker.vue";
import PropertyPanel from "@/components/editor/PropertyPanel.vue";
import Toolbar from "@/components/editor/Toolbar.vue";
import SiteNav from "@/components/layout/SiteNav.vue";
import ModeToggle from "@/components/layout/ModeToggle.vue";
import ConnectionBanner from "@/components/shared/ConnectionBanner.vue";

const planStore = usePlanStore();
const editorStore = useEditorStore();
const liveStore = useLiveStore();

// Live WebSocket connection
useWebSocket(() => planStore.currentPlanId);

const plansList = ref<Array<{ id: string; name: string }>>([]);
const showNewPlanModal = ref(false);
const newPlanName = ref("");

async function loadPlans() {
  try {
    const res = await api.listPlans();
    plansList.value = res.plans;
    if (res.plans.length > 0 && !planStore.currentPlanId) {
      await planStore.loadPlan(res.plans[0].id);
    } else if (res.plans.length === 0) {
      const created = await api.createPlan("Home Security Plan");
      plansList.value = [{ id: created.id, name: created.plan.name }];
      await planStore.loadPlan(created.id);
    }
  } catch (err) {
    console.error("Failed to load initial plans", err);
  }
}

async function handleCreatePlan() {
  if (!newPlanName.value.trim()) return;
  try {
    const created = await api.createPlan(newPlanName.value.trim());
    plansList.value.push({ id: created.id, name: created.plan.name });
    await planStore.loadPlan(created.id);
    newPlanName.value = "";
    showNewPlanModal.value = false;
  } catch (err: any) {
    alert(err.message || "Failed to create plan");
  }
}

async function handleSwitchPlan(e: Event) {
  const target = e.target as HTMLSelectElement;
  if (target.value) {
    await planStore.loadPlan(target.value);
  }
}

onMounted(() => {
  loadPlans();
});
</script>

<template>
  <div class="app-shell">
    <ConnectionBanner />

    <!-- Top Navigation Bar -->
    <header class="app-header glass-panel">
      <!-- Brand & Plan Selector -->
      <div class="brand-section">
        <div class="logo">
          <svg viewBox="0 0 24 24" width="22" height="22">
            <path fill="#6366f1" d="M12 2L3 7v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V7l-9-5zm0 4.18l6 3.33v3.74c0 3.73-2.55 7.21-6 8.35-3.45-1.14-6-4.62-6-8.35v-3.74l6-3.33z"/>
          </svg>
          <span class="app-title">Security Hawk</span>
        </div>

        <div class="plan-selector">
          <select :value="planStore.currentPlanId" @change="handleSwitchPlan">
            <option v-for="p in plansList" :key="p.id" :value="p.id">
              {{ p.name }}
            </option>
          </select>
          <button class="add-plan-btn" title="Create new plan" @click="showNewPlanModal = true">+</button>
        </div>
      </div>

      <!-- Floor / Building Navigation -->
      <div class="center-section">
        <SiteNav />
      </div>

      <!-- Right Controls: Mode Toggle & Status -->
      <div class="right-section">
        <ModeToggle />
        <div class="ws-pill" :class="{ connected: liveStore.isConnected }" :title="liveStore.isConnected ? 'Connected to HA' : 'Disconnected from HA'">
          <span class="ws-dot"></span>
          <span class="ws-label">{{ liveStore.isConnected ? 'Live' : 'Offline' }}</span>
        </div>
      </div>
    </header>

    <!-- Main Workspace -->
    <main class="app-workspace">
      <!-- Design Mode: Editor Canvas + Sidebar Panels + Toolbar -->
      <template v-if="editorStore.mode === 'design'">
        <EntityPicker />
        <div class="canvas-wrapper">
          <Toolbar />
          <EditorCanvas />
        </div>
        <PropertyPanel />
      </template>

      <!-- Usage Mode: Full-screen Live Canvas -->
      <template v-else>
        <div class="canvas-wrapper full-live">
          <LiveCanvas />
        </div>
      </template>
    </main>

    <!-- Create Plan Dialog -->
    <div v-if="showNewPlanModal" class="modal-overlay" @click="showNewPlanModal = false">
      <div class="modal-box glass-panel" @click.stop>
        <div class="modal-title">Create New Floor Plan</div>
        <input
          type="text"
          v-model="newPlanName"
          placeholder="e.g. Ground Floor & Garden"
          autofocus
          @keyup.enter="handleCreatePlan"
        />
        <div class="modal-actions">
          <button class="btn-cancel" @click="showNewPlanModal = false">Cancel</button>
          <button class="btn-confirm" @click="handleCreatePlan">Create</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.app-shell {
  width: 100vw;
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: relative;
  background-color: var(--bg-primary);
}

.app-header {
  height: 54px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  border-radius: 0;
  border-left: none;
  border-right: none;
  border-top: none;
  z-index: 200;
  flex-shrink: 0;
}

.brand-section {
  display: flex;
  align-items: center;
  gap: 16px;
}

.logo {
  display: flex;
  align-items: center;
  gap: 8px;
}

.app-title {
  font-size: 15px;
  font-weight: 700;
  letter-spacing: -0.3px;
  background: linear-gradient(135deg, #f8fafc 0%, #cbd5e1 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.plan-selector {
  display: flex;
  align-items: center;
  gap: 6px;
}

.plan-selector select {
  font-size: 12px;
  padding: 4px 8px;
  height: 28px;
}

.add-plan-btn {
  width: 28px;
  height: 28px;
  background: var(--bg-surface);
  color: var(--text-primary);
  border-radius: var(--radius-sm);
  font-size: 16px;
  font-weight: 500;
  display: flex;
  align-items: center;
  justify-content: center;
}

.add-plan-btn:hover {
  background: var(--accent-primary);
}

.center-section {
  display: flex;
  align-items: center;
}

.right-section {
  display: flex;
  align-items: center;
  gap: 12px;
}

.ws-pill {
  display: flex;
  align-items: center;
  gap: 6px;
  background: rgba(239, 68, 68, 0.15);
  border: 1px solid rgba(239, 68, 68, 0.3);
  padding: 4px 10px;
  border-radius: var(--radius-full);
  font-size: 11px;
  font-weight: 500;
  color: var(--color-danger);
}

.ws-pill.connected {
  background: rgba(16, 185, 129, 0.15);
  border-color: rgba(16, 185, 129, 0.3);
  color: var(--color-success);
}

.ws-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}

.ws-pill.connected .ws-dot {
  box-shadow: 0 0 6px var(--color-success);
}

.app-workspace {
  flex: 1;
  display: flex;
  position: relative;
  overflow: hidden;
}

.canvas-wrapper {
  flex: 1;
  height: 100%;
  position: relative;
}

.canvas-wrapper.full-live {
  width: 100%;
}

/* Modal styles */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-box {
  width: 320px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.modal-title {
  font-size: 15px;
  font-weight: 600;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.btn-cancel {
  padding: 6px 12px;
  background: var(--bg-surface);
  color: var(--text-secondary);
  border-radius: var(--radius-sm);
  font-size: 13px;
}

.btn-confirm {
  padding: 6px 14px;
  background: var(--accent-primary);
  color: #ffffff;
  border-radius: var(--radius-sm);
  font-size: 13px;
  font-weight: 500;
}
</style>
