<script setup lang="ts">
import { ref, onMounted, onUnmounted } from "vue";
import { api } from "@/services/api";
import type { Endpoint } from "@/types/plan";

const props = defineProps<{
  endpoint: Endpoint;
}>();

const emit = defineEmits<{
  (e: "close"): void;
}>();

const snapshotUrl = ref<string>("");
const lastUpdatedTime = ref<string>("");
const isMaximized = ref(false);
const modalContainerRef = ref<HTMLDivElement | null>(null);
let refreshTimer: number | null = null;

function refreshSnapshot() {
  snapshotUrl.value = api.getCameraSnapshotUrl(props.endpoint.entity_id);
  const now = new Date();
  lastUpdatedTime.value = now.toLocaleTimeString();
}

function handleKeydown(e: KeyboardEvent) {
  // Remote back button or Escape key
  if (
    e.key === "Escape" ||
    e.key === "BrowserBack" ||
    e.key === "GoBack" ||
    e.key === "Back" ||
    e.keyCode === 27 ||
    e.keyCode === 4
  ) {
    e.preventDefault();
    e.stopPropagation();
    emit("close");
  }
}

function toggleMaximize() {
  isMaximized.value = !isMaximized.value;
}

onMounted(() => {
  refreshSnapshot();
  // Auto-refresh snapshot every 2.5 seconds
  refreshTimer = window.setInterval(refreshSnapshot, 2500);

  window.addEventListener("keydown", handleKeydown, true);

  // Focus modal container so keyboard/remote events route properly
  modalContainerRef.value?.focus();
});

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer);
  window.removeEventListener("keydown", handleKeydown, true);
});
</script>

<template>
  <div class="window-backdrop" @click="emit('close')">
    <div
      ref="modalContainerRef"
      class="camera-window glass-panel"
      :class="{ maximized: isMaximized }"
      tabindex="-1"
      @click.stop
    >
      <!-- Window Title Bar -->
      <div class="window-titlebar">
        <div class="title-left">
          <span class="live-dot" title="Live stream"></span>
          <span class="window-title">{{ endpoint.label || endpoint.entity_id }}</span>
          <span class="window-badge">LIVE CAMERA</span>
        </div>

        <div class="window-controls">
          <button
            class="control-btn"
            :title="isMaximized ? 'Restore window' : 'Maximize window'"
            @click="toggleMaximize"
          >
            <svg v-if="!isMaximized" viewBox="0 0 24 24" width="14" height="14">
              <path fill="currentColor" d="M4 4h16v16H4V4zm2 4v10h12V8H6z"/>
            </svg>
            <svg v-else viewBox="0 0 24 24" width="14" height="14">
              <path fill="currentColor" d="M4 8H2V2h6v2H4v4zm10-6h6v6h-2V4h-4V2zM2 16h2v4h4v2H2v-6zm18 4h-4v2h6v-6h-2v4z"/>
            </svg>
          </button>
          <button
            class="control-btn close"
            title="Close window (Esc / Back)"
            @click="emit('close')"
          >
            <svg viewBox="0 0 24 24" width="16" height="16">
              <path fill="currentColor" d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12 19 6.41z"/>
            </svg>
          </button>
        </div>
      </div>

      <!-- Camera Feed Display -->
      <div class="window-body">
        <img
          :src="snapshotUrl"
          :alt="endpoint.label || 'Camera Feed'"
          class="camera-stream"
          @error="() => {}"
        />
      </div>

      <!-- Window Status Bar -->
      <div class="window-statusbar">
        <div class="status-left">
          <span class="status-entity">{{ endpoint.entity_id }}</span>
          <span class="status-sep" v-if="lastUpdatedTime">•</span>
          <span class="status-time" v-if="lastUpdatedTime">Updated {{ lastUpdatedTime }}</span>
        </div>

        <div class="status-right">
          <span class="key-hint">Press <strong>ESC</strong> or <strong>Back</strong> to close</span>
          <button class="action-btn" @click="refreshSnapshot">Refresh</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.window-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(6px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  padding: 24px;
}

.camera-window {
  width: 720px;
  max-width: 95vw;
  background: #0f172a;
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: var(--radius-md);
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.8), 0 0 30px var(--accent-primary-glow);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
  outline: none;
}

.camera-window.maximized {
  width: 98vw;
  height: 94vh;
  max-width: 100vw;
}

.window-titlebar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #1e293b;
  border-bottom: 1px solid var(--border-color);
  user-select: none;
}

.title-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.live-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background-color: var(--color-danger);
  animation: pulse-glow 1.5s infinite;
}

.window-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.window-badge {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.5px;
  padding: 2px 6px;
  background: rgba(99, 102, 241, 0.2);
  color: #a5b4fc;
  border-radius: var(--radius-sm);
  border: 1px solid rgba(99, 102, 241, 0.4);
}

.window-controls {
  display: flex;
  align-items: center;
  gap: 6px;
}

.control-btn {
  width: 28px;
  height: 28px;
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
  background: rgba(255, 255, 255, 0.05);
}

.control-btn:hover {
  background: rgba(255, 255, 255, 0.15);
  color: var(--text-primary);
}

.control-btn.close:hover {
  background: var(--color-danger);
  color: #ffffff;
}

.window-body {
  width: 100%;
  height: 440px;
  background: #000000;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  position: relative;
}

.camera-window.maximized .window-body {
  flex: 1;
  height: 100%;
}

.camera-stream {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.window-statusbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 16px;
  background: #1e293b;
  border-top: 1px solid var(--border-color);
  font-size: 12px;
  color: var(--text-muted);
}

.status-left {
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: var(--font-mono);
  font-size: 11px;
}

.status-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.key-hint {
  font-size: 11px;
  color: var(--text-secondary);
}

.key-hint strong {
  color: #ffffff;
  background: rgba(255, 255, 255, 0.1);
  padding: 2px 5px;
  border-radius: 4px;
}

.action-btn {
  padding: 4px 10px;
  background: var(--bg-surface);
  color: var(--text-primary);
  border-radius: var(--radius-sm);
  font-size: 11px;
  font-weight: 500;
}

.action-btn:hover {
  background: var(--accent-primary);
}
</style>
