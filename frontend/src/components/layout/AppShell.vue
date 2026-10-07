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
import CadCommandBar from "@/components/editor/CadCommandBar.vue";
import RoomGridModal from "@/components/editor/RoomGridModal.vue";
import ExportPlanModal from "@/components/editor/ExportPlanModal.vue";
import VersionHistoryModal from "@/components/editor/VersionHistoryModal.vue";
import CoverageAuditModal from "@/components/editor/CoverageAuditModal.vue";
import SiteNav from "@/components/layout/SiteNav.vue";
import ModeToggle from "@/components/layout/ModeToggle.vue";
import ConnectionBanner from "@/components/shared/ConnectionBanner.vue";
import SettingsModal from "@/components/settings/SettingsModal.vue";

const planStore = usePlanStore();
const editorStore = useEditorStore();
const liveStore = useLiveStore();

// Live WebSocket connection
useWebSocket(() => planStore.currentPlanId);

const plansList = ref<Array<{ id: string; name: string }>>([]);
const showNewPlanModal = ref(false);
const showSettingsModal = ref(false);
const settingsInitialTab = ref<"behaviors" | "mqtt" | "helpers" | "notifications" | "kiosk">("behaviors");
const newPlanName = ref("");
const appVersion = ref(typeof __APP_VERSION__ !== "undefined" ? __APP_VERSION__ : "0.4.2");

function openKioskTab() {
  settingsInitialTab.value = "kiosk";
  showSettingsModal.value = true;
}

function openSettings(tab: "behaviors" | "mqtt" | "helpers" | "notifications" | "kiosk" = "behaviors") {
  settingsInitialTab.value = tab;
  showSettingsModal.value = true;
}

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
  editorStore.setWorkspacePreset("mapping");
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
          <span class="app-version-badge" title="Installed Application Version">v{{ appVersion }}</span>
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

      <!-- Right Controls: Mode Toggle, Viewers, Settings & Status -->
      <div class="right-section">
        <ModeToggle />

        <!-- Active Viewers Pill -->
        <div
          class="viewers-pill"
          :title="`${liveStore.viewerCount} screen(s) viewing this plan (${liveStore.totalViewers} total). Click to view kiosk links.`"
          @click="openKioskTab"
        >
          <span class="viewers-icon">👁️</span>
          <span class="viewers-count">{{ liveStore.viewerCount }}</span>
          <span class="viewers-label">{{ liveStore.viewerCount === 1 ? 'screen' : 'screens' }}</span>
        </div>

        <button
          class="settings-btn"
          title="Application Settings (MQTT, Behaviors, Kiosk Links, HA Helpers)"
          @click="openSettings('behaviors')"
        >
          <svg viewBox="0 0 24 24" width="16" height="16">
            <path fill="currentColor" d="M12 15.5A3.5 3.5 0 0 1 8.5 12A3.5 3.5 0 0 1 12 8.5A3.5 3.5 0 0 1 15.5 12A3.5 3.5 0 0 1 12 15.5M19.43 12.97C19.47 12.65 19.5 12.33 19.5 12C19.5 11.67 19.47 11.34 19.43 11L21.54 9.37C21.73 9.22 21.78 8.95 21.66 8.73L19.66 5.27C19.54 5.05 19.27 4.97 19.05 5.05L16.56 6.05C16.04 5.65 15.48 5.32 14.87 5.07L14.49 2.42C14.46 2.18 14.25 2 14 2H10C9.75 2 9.54 2.18 9.51 2.42L9.13 5.07C8.52 5.32 7.96 5.66 7.44 6.05L4.95 5.05C4.73 4.96 4.46 5.05 4.34 5.27L2.34 8.73C2.21 8.95 2.27 9.22 2.46 9.37L4.57 11C4.53 11.34 4.5 11.67 4.5 12C4.5 12.33 4.53 12.65 4.57 12.97L2.46 14.63C2.27 14.78 2.21 15.05 2.34 15.27L4.34 18.73C4.46 18.95 4.73 19.03 4.95 18.95L7.44 17.95C7.96 18.35 8.52 18.68 9.13 18.93L9.51 21.58C9.54 21.82 9.75 22 10 22H14C14.25 22 14.46 21.82 14.49 21.58L14.87 18.93C15.48 18.68 16.04 18.34 16.56 17.95L19.05 18.95C19.27 19.04 19.54 18.95 19.66 18.73L21.66 15.27C21.78 15.05 21.73 14.78 21.54 14.63L19.43 12.97Z"/>
          </svg>
        </button>
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
          <CadCommandBar
            v-if="editorStore.showCadCommandBar"
            @open-grid-modal="editorStore.showRoomGridModal = true"
            @open-export-modal="editorStore.showExportModal = true"
            @open-history-modal="editorStore.showVersionModal = true"
          />
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

    <!-- Room Grid Matrix Modal -->
    <RoomGridModal
      v-if="editorStore.showRoomGridModal"
      @close="editorStore.showRoomGridModal = false"
    />

    <!-- Export Plan Modal -->
    <ExportPlanModal
      v-if="editorStore.showExportModal && planStore.currentPlanId"
      :plan-id="planStore.currentPlanId"
      @close="editorStore.showExportModal = false"
    />

    <!-- Version History Modal -->
    <VersionHistoryModal
      v-if="editorStore.showVersionModal && planStore.currentPlanId"
      :plan-id="planStore.currentPlanId"
      @close="editorStore.showVersionModal = false"
    />

    <!-- AI Security Coverage Audit Modal -->
    <CoverageAuditModal
      :show="editorStore.showCoverageAuditModal"
      @close="editorStore.showCoverageAuditModal = false"
    />

    <!-- Application & Integration Settings Modal -->
    <SettingsModal
      :show="showSettingsModal"
      :initial-tab="settingsInitialTab"
      :plans="plansList"
      @close="showSettingsModal = false"
    />
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
  background-clip: text;
  -webkit-text-fill-color: transparent;
}

.app-version-badge {
  font-size: 10px;
  font-weight: 600;
  font-family: var(--font-mono, monospace);
  padding: 1px 5px;
  border-radius: 4px;
  background: rgba(99, 102, 241, 0.15);
  color: #a5b4fc;
  border: 1px solid rgba(99, 102, 241, 0.3);
  letter-spacing: 0.5px;
  line-height: 1.2;
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

.settings-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all 0.15s ease;
}

.settings-btn:hover {
  background: rgba(99, 102, 241, 0.2);
  border-color: var(--accent-primary);
  color: #ffffff;
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
  overflow: hidden;
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

.viewers-pill {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 4px 10px;
  background: rgba(99, 102, 241, 0.12);
  border: 1px solid rgba(99, 102, 241, 0.3);
  border-radius: 20px;
  font-size: 11px;
  color: #c7d2fe;
  cursor: pointer;
  transition: all 0.2s;
  user-select: none;
}

.viewers-pill:hover {
  background: rgba(99, 102, 241, 0.22);
  border-color: #818cf8;
  color: #ffffff;
  transform: translateY(-1px);
}

.viewers-icon {
  font-size: 13px;
}

.viewers-count {
  font-weight: 700;
  color: #818cf8;
}

.viewers-label {
  font-size: 10px;
  color: var(--text-muted);
}
</style>
