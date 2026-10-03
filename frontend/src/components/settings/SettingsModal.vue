<script setup lang="ts">
import { ref, watch } from "vue";
import type { AppSettings } from "@/types/plan";
import { api } from "@/services/api";

const props = defineProps<{
  show: boolean;
}>();

const emit = defineEmits<{
  (e: "close"): void;
  (e: "saved", settings: AppSettings): void;
}>();

const activeTab = ref<"behaviors" | "mqtt" | "helpers">("behaviors");

const quietReturnSeconds = ref(120);
const autoDismissCameraSeconds = ref(30);
const defaultView = ref<"overview" | "floor">("overview");

// MQTT
const mqttEnabled = ref(false);
const mqttHost = ref("core-mosquitto");
const mqttPort = ref(1883);
const mqttUsername = ref("");
const mqttPassword = ref("");
const mqttTopicPrefix = ref("security_hawk/");
const mqttHaDiscovery = ref(true);

// Helpers
const autoRegisterSynthetic = ref(true);
const helperPrefix = ref("security_hawk_");

const isLoading = ref(false);
const isSaving = ref(false);
const isSyncingHelpers = ref(false);
const syncResult = ref<{ count: number; results: Array<{ rule_id: string; entity_id: string; ok: boolean }> } | null>(null);
const errorMessage = ref<string | null>(null);
const successMessage = ref<string | null>(null);

watch(
  () => props.show,
  async (isShowing) => {
    if (isShowing) {
      errorMessage.value = null;
      successMessage.value = null;
      syncResult.value = null;
      try {
        isLoading.value = true;
        const res = await api.getSettings();
        const s = res.settings;
        quietReturnSeconds.value = s.quiet_return_seconds ?? 120;
        autoDismissCameraSeconds.value = s.auto_dismiss_camera_seconds ?? 30;
        defaultView.value = s.default_view ?? "overview";

        mqttEnabled.value = s.mqtt?.enabled ?? false;
        mqttHost.value = s.mqtt?.host || "core-mosquitto";
        mqttPort.value = s.mqtt?.port || 1883;
        mqttUsername.value = s.mqtt?.username || "";
        mqttPassword.value = s.mqtt?.password || "";
        mqttTopicPrefix.value = s.mqtt?.topic_prefix || "security_hawk/";
        mqttHaDiscovery.value = s.mqtt?.ha_discovery ?? true;

        autoRegisterSynthetic.value = s.helpers?.auto_register_synthetic_sensors ?? true;
        helperPrefix.value = s.helpers?.prefix || "security_hawk_";
      } catch (err: any) {
        errorMessage.value = err.message || "Failed to load settings.";
      } finally {
        isLoading.value = false;
      }
    }
  },
  { immediate: true }
);

async function handleSave() {
  try {
    isSaving.value = true;
    errorMessage.value = null;
    successMessage.value = null;

    const payload: Partial<AppSettings> = {
      quiet_return_seconds: Number(quietReturnSeconds.value),
      auto_dismiss_camera_seconds: Number(autoDismissCameraSeconds.value),
      default_view: defaultView.value,
      mqtt: {
        enabled: mqttEnabled.value,
        host: mqttHost.value.trim(),
        port: Number(mqttPort.value),
        username: mqttUsername.value.trim(),
        password: mqttPassword.value,
        topic_prefix: mqttTopicPrefix.value.trim(),
        ha_discovery: mqttHaDiscovery.value,
      },
      helpers: {
        auto_register_synthetic_sensors: autoRegisterSynthetic.value,
        prefix: helperPrefix.value.trim(),
      },
    };

    const res = await api.saveSettings(payload);
    successMessage.value = "Settings saved successfully.";
    emit("saved", res.settings);
    setTimeout(() => {
      emit("close");
    }, 800);
  } catch (err: any) {
    errorMessage.value = err.message || "Failed to save settings.";
  } finally {
    isSaving.value = false;
  }
}

async function handleSyncHelpers() {
  try {
    isSyncingHelpers.value = true;
    errorMessage.value = null;
    syncResult.value = null;
    const res = await api.registerHAHelpers();
    syncResult.value = { count: res.count, results: res.results };
  } catch (err: any) {
    errorMessage.value = err.message || "Failed to register HA synthetic helpers.";
  } finally {
    isSyncingHelpers.value = false;
  }
}
</script>

<template>
  <div v-if="show" class="modal-backdrop" @click.self="emit('close')">
    <div class="settings-modal glass-panel">
      <!-- Modal Header -->
      <div class="modal-header">
        <div class="header-info">
          <div class="title-row">
            <span class="header-icon">⚙️</span>
            <h2>Application & Integration Settings</h2>
          </div>
          <p class="subtitle">
            Configure system behaviors, MQTT information store, and Home Assistant synthetic helpers.
          </p>
        </div>
        <button class="close-btn" @click="emit('close')">✕</button>
      </div>

      <!-- Settings Nav Tabs -->
      <div class="settings-nav">
        <button
          type="button"
          class="nav-tab"
          :class="{ active: activeTab === 'behaviors' }"
          @click="activeTab = 'behaviors'"
        >
          <span class="tab-icon">⏱️</span> Default Behaviors
        </button>
        <button
          type="button"
          class="nav-tab"
          :class="{ active: activeTab === 'mqtt' }"
          @click="activeTab = 'mqtt'"
        >
          <span class="tab-icon">📡</span> MQTT Information Store
        </button>
        <button
          type="button"
          class="nav-tab"
          :class="{ active: activeTab === 'helpers' }"
          @click="activeTab = 'helpers'"
        >
          <span class="tab-icon">✨</span> HA Helpers & Entities
        </button>
      </div>

      <!-- Modal Body -->
      <div class="modal-body">
        <div v-if="isLoading" class="loading-state">
          Loading settings...
        </div>

        <template v-else>
          <div v-if="errorMessage" class="alert-box error">
            {{ errorMessage }}
          </div>
          <div v-if="successMessage" class="alert-box success">
            {{ successMessage }}
          </div>

          <!-- TAB 1: BEHAVIORS -->
          <div v-if="activeTab === 'behaviors'" class="tab-content">
            <div class="form-section">
              <div class="section-title">Automation & Display Behaviors</div>

              <div class="form-group">
                <label>Quiet Return Timeout (seconds)</label>
                <div class="slider-row">
                  <input
                    v-model.number="quietReturnSeconds"
                    type="range"
                    min="15"
                    max="600"
                    step="15"
                  />
                  <span class="badge-val">{{ quietReturnSeconds }}s</span>
                </div>
                <span class="field-hint">
                  In Follow-Activity mode, return automatically to the Site Overview after this duration of inactivity.
                </span>
              </div>

              <div class="form-group">
                <label>Camera Snapshot Popup Timeout (seconds)</label>
                <div class="slider-row">
                  <input
                    v-model.number="autoDismissCameraSeconds"
                    type="range"
                    min="5"
                    max="120"
                    step="5"
                  />
                  <span class="badge-val">{{ autoDismissCameraSeconds }}s</span>
                </div>
                <span class="field-hint">
                  Auto-dismiss camera snapshot feeds after this duration (hovering pauses the timer).
                </span>
              </div>

              <div class="form-group">
                <label>Default Startup View</label>
                <div class="toggle-pill-group">
                  <button
                    type="button"
                    class="toggle-pill"
                    :class="{ active: defaultView === 'overview' }"
                    @click="defaultView = 'overview'"
                  >
                    Site Overview (Multi-Floor)
                  </button>
                  <button
                    type="button"
                    class="toggle-pill"
                    :class="{ active: defaultView === 'floor' }"
                    @click="defaultView = 'floor'"
                  >
                    Primary Floor Plan
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- TAB 2: MQTT INFORMATION STORE -->
          <div v-if="activeTab === 'mqtt'" class="tab-content">
            <div class="form-section">
              <div class="section-title">MQTT Broker & HA Discovery</div>
              <p class="section-desc">
                Publish live floor plan events and compound rule triggers to your MQTT broker with automatic Home Assistant MQTT Discovery.
              </p>

              <div class="form-group">
                <label class="checkbox-label">
                  <input type="checkbox" v-model="mqttEnabled" />
                  <span class="bold">Enable MQTT Information Store</span>
                </label>
              </div>

              <div v-if="mqttEnabled" class="mqtt-form-grid">
                <div class="form-row">
                  <div class="form-group flex-2">
                    <label>Broker Host</label>
                    <input v-model="mqttHost" type="text" placeholder="core-mosquitto" />
                    <span class="field-hint">Use <code>core-mosquitto</code> inside Home Assistant OS or your external IP/hostname.</span>
                  </div>
                  <div class="form-group flex-1">
                    <label>Port</label>
                    <input v-model.number="mqttPort" type="number" placeholder="1883" />
                  </div>
                </div>

                <div class="form-row">
                  <div class="form-group flex-1">
                    <label>Username (optional)</label>
                    <input v-model="mqttUsername" type="text" placeholder="mqtt_user" />
                  </div>
                  <div class="form-group flex-1">
                    <label>Password (optional)</label>
                    <input v-model="mqttPassword" type="password" placeholder="••••••••" />
                  </div>
                </div>

                <div class="form-group">
                  <label>Topic Prefix</label>
                  <input v-model="mqttTopicPrefix" type="text" placeholder="security_hawk/" />
                </div>

                <div class="form-group">
                  <label class="checkbox-label">
                    <input type="checkbox" v-model="mqttHaDiscovery" />
                    <span>Publish Home Assistant MQTT Discovery Payloads (<code>homeassistant/binary_sensor/security_hawk_*/config</code>)</span>
                  </label>
                </div>
              </div>
            </div>
          </div>

          <!-- TAB 3: HELPERS & SYNTHETIC ENTITIES -->
          <div v-if="activeTab === 'helpers'" class="tab-content">
            <div class="form-section">
              <div class="section-title">Native Home Assistant Synthetic Helpers</div>
              <p class="section-desc">
                Security Hawk creates synthetic binary sensors directly in Home Assistant Core's native state engine.
                No YAML edits, restart, or external dependencies required.
              </p>

              <div class="form-group">
                <label class="checkbox-label">
                  <input type="checkbox" v-model="autoRegisterSynthetic" />
                  <span class="bold">Auto-register and keep synthetic sensors active in HA Core</span>
                </label>
              </div>

              <div class="form-group">
                <label>Helper Prefix</label>
                <input v-model="helperPrefix" type="text" placeholder="security_hawk_" />
                <span class="field-hint">Prefix used for generated entities (e.g. <code>binary_sensor.security_hawk_...</code>).</span>
              </div>

              <div class="sync-actions-box">
                <div class="sync-info">
                  <strong>On-Demand Sync to Home Assistant</strong>
                  <p>Register all defined compound rules as native sensors immediately.</p>
                </div>
                <button
                  type="button"
                  class="btn-sync"
                  :disabled="isSyncingHelpers"
                  @click="handleSyncHelpers"
                >
                  {{ isSyncingHelpers ? 'Syncing...' : '⚡ Register in Home Assistant' }}
                </button>
              </div>

              <div v-if="syncResult" class="sync-results">
                <div class="sync-summary">
                  Registered {{ syncResult.count }} synthetic helper(s):
                </div>
                <div class="helper-pill-list">
                  <div
                    v-for="r in syncResult.results"
                    :key="r.entity_id"
                    class="helper-pill"
                    :class="{ ok: r.ok, fail: !r.ok }"
                  >
                    <span>{{ r.ok ? '✓' : '✕' }}</span>
                    <code>{{ r.entity_id }}</code>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </template>
      </div>

      <!-- Modal Footer -->
      <div class="modal-footer">
        <button type="button" class="btn-secondary" @click="emit('close')">
          Cancel
        </button>
        <button
          type="button"
          class="btn-primary"
          :disabled="isSaving || isLoading"
          @click="handleSave"
        >
          {{ isSaving ? 'Saving...' : 'Save Settings' }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

.settings-modal {
  width: 100%;
  max-width: 720px;
  max-height: 88vh;
  display: flex;
  flex-direction: column;
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-color);
  background: var(--bg-surface);
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.6);
  overflow: hidden;
}

.modal-header {
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
}

.title-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.header-icon {
  font-size: 20px;
}

.modal-header h2 {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.subtitle {
  font-size: 12px;
  color: var(--text-muted);
  margin: 4px 0 0;
}

.close-btn {
  background: transparent;
  border: none;
  font-size: 18px;
  color: var(--text-muted);
  cursor: pointer;
  padding: 4px 8px;
  border-radius: var(--radius-sm);
}

.close-btn:hover {
  color: var(--text-primary);
  background: rgba(255, 255, 255, 0.05);
}

.settings-nav {
  display: flex;
  background: rgba(15, 23, 42, 0.7);
  border-bottom: 1px solid var(--border-color);
  padding: 0 16px;
  gap: 8px;
}

.nav-tab {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 14px;
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}

.nav-tab:hover {
  color: var(--text-primary);
}

.nav-tab.active {
  color: var(--accent-primary);
  border-bottom-color: var(--accent-primary);
}

.modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.loading-state {
  text-align: center;
  padding: 40px;
  color: var(--text-muted);
}

.alert-box {
  padding: 10px 14px;
  border-radius: var(--radius-sm);
  font-size: 13px;
  font-weight: 500;
  margin-bottom: 16px;
}

.alert-box.error {
  background: rgba(239, 68, 68, 0.15);
  color: #fca5a5;
  border: 1px solid rgba(239, 68, 68, 0.3);
}

.alert-box.success {
  background: rgba(16, 185, 129, 0.15);
  color: #6ee7b7;
  border: 1px solid rgba(16, 185, 129, 0.3);
}

.form-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.section-title {
  font-size: 13px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--accent-primary);
}

.section-desc {
  font-size: 12px;
  color: var(--text-muted);
  line-height: 1.5;
  margin: -8px 0 4px;
}

.form-row {
  display: flex;
  gap: 16px;
}

.flex-1 {
  flex: 1;
}

.flex-2 {
  flex: 2;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-group label {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary);
}

.field-hint {
  font-size: 11px;
  color: var(--text-muted);
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  color: var(--text-primary);
}

.bold {
  font-weight: 600;
}

.slider-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.slider-row input[type="range"] {
  flex: 1;
}

.badge-val {
  background: rgba(99, 102, 241, 0.2);
  color: var(--accent-primary);
  font-size: 12px;
  font-weight: 600;
  padding: 3px 8px;
  border-radius: var(--radius-sm);
  min-width: 48px;
  text-align: center;
}

.toggle-pill-group {
  display: flex;
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid var(--border-color);
  padding: 3px;
  border-radius: var(--radius-sm);
  gap: 4px;
}

.toggle-pill {
  flex: 1;
  padding: 7px 12px;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary);
  background: transparent;
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all 0.15s ease;
}

.toggle-pill.active {
  background: var(--accent-primary);
  color: #ffffff;
}

.mqtt-form-grid {
  display: flex;
  flex-direction: column;
  gap: 14px;
  background: rgba(15, 23, 42, 0.4);
  padding: 14px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-color);
}

.sync-actions-box {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: rgba(15, 23, 42, 0.5);
  border: 1px solid var(--border-color);
  padding: 14px;
  border-radius: var(--radius-sm);
  margin-top: 6px;
}

.sync-info strong {
  font-size: 13px;
  color: var(--text-primary);
}

.sync-info p {
  font-size: 11px;
  color: var(--text-muted);
  margin: 2px 0 0;
}

.btn-sync {
  background: rgba(99, 102, 241, 0.2);
  border: 1px solid var(--accent-primary);
  color: #a5b4fc;
  padding: 8px 14px;
  border-radius: var(--radius-sm);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
  white-space: nowrap;
}

.btn-sync:hover:not(:disabled) {
  background: rgba(99, 102, 241, 0.35);
  color: #ffffff;
}

.sync-results {
  background: rgba(15, 23, 42, 0.4);
  border: 1px solid var(--border-color);
  padding: 12px;
  border-radius: var(--radius-sm);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.sync-summary {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary);
}

.helper-pill-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.helper-pill {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  padding: 3px 8px;
  border-radius: var(--radius-full);
}

.helper-pill.ok {
  background: rgba(16, 185, 129, 0.15);
  color: #6ee7b7;
  border: 1px solid rgba(16, 185, 129, 0.3);
}

.helper-pill.fail {
  background: rgba(239, 68, 68, 0.15);
  color: #fca5a5;
  border: 1px solid rgba(239, 68, 68, 0.3);
}

.modal-footer {
  padding: 16px 20px;
  border-top: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
}

.btn-primary {
  background: var(--accent-primary);
  color: #ffffff;
  padding: 7px 16px;
  border-radius: var(--radius-sm);
  font-size: 12px;
  font-weight: 600;
  border: none;
  cursor: pointer;
}

.btn-primary:hover:not(:disabled) {
  opacity: 0.9;
}

.btn-secondary {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  padding: 7px 14px;
  border-radius: var(--radius-sm);
  font-size: 12px;
  cursor: pointer;
}

.btn-secondary:hover {
  color: var(--text-primary);
  background: rgba(255, 255, 255, 0.1);
}
</style>
