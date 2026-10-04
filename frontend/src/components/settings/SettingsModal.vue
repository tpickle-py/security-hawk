<script setup lang="ts">
import { computed, ref, watch } from "vue";
import type { AppSettings, KioskStatus, DockCorner, ToolbarDockPosition } from "@/types/plan";
import { api, getBasePath } from "@/services/api";
import { useLiveStore, DEFAULT_DOCK_POSITIONS } from "@/stores/liveStore";
import { useEditorStore } from "@/stores/editorStore";

const props = defineProps<{
  show: boolean;
  initialTab?: "behaviors" | "mqtt" | "helpers" | "notifications" | "kiosk";
  plans?: Array<{ id: string; name: string }>;
}>();

const emit = defineEmits<{
  (e: "close"): void;
  (e: "saved", settings: AppSettings): void;
}>();

const liveStore = useLiveStore();
const editorStore = useEditorStore();

const activeTab = ref<"behaviors" | "mqtt" | "helpers" | "notifications" | "kiosk">(
  props.initialTab || "behaviors"
);

const quietReturnSeconds = ref(120);
const autoDismissCameraSeconds = ref(30);
const defaultView = ref<"overview" | "floor">("overview");

// Docked Menus Layout
const activityFeedDock = ref<DockCorner>("bottom-left");
const navControlsDock = ref<DockCorner>("bottom-right");
const toolbarDock = ref<ToolbarDockPosition>("top");

const cornerOptions: Array<{ label: string; value: DockCorner; desc: string }> = [
  { label: "Bottom Left", value: "bottom-left", desc: "Lower left corner" },
  { label: "Bottom Right", value: "bottom-right", desc: "Lower right corner" },
  { label: "Top Left", value: "top-left", desc: "Upper left below topbar" },
  { label: "Top Right", value: "top-right", desc: "Upper right below topbar" },
];

const toolbarDockOptions: Array<{ label: string; value: ToolbarDockPosition }> = [
  { label: "Top Center (Default)", value: "top" },
  { label: "Bottom Center", value: "bottom" },
  { label: "Left Side", value: "left" },
  { label: "Right Side", value: "right" },
];

const isDockOverlapping = computed(() => activityFeedDock.value === navControlsDock.value);

function handleResetDockPositions() {
  activityFeedDock.value = DEFAULT_DOCK_POSITIONS.activity_feed;
  navControlsDock.value = DEFAULT_DOCK_POSITIONS.nav_controls;
  toolbarDock.value = "top";
  liveStore.resetDockPositions();
  editorStore.resetToolbarDock();
}

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

// Notification Defaults
const emailHost = ref("");
const emailPort = ref(587);
const emailUser = ref("");
const emailPassword = ref("");
const emailFrom = ref("");
const emailDefaultTo = ref("");
const emailUseTls = ref(true);

const waProvider = ref("callmebot");
const waDefaultPhone = ref("");
const waApiKey = ref("");
const waAccountSid = ref("");
const waFromPhone = ref("");

// Kiosk & Share Links State
const kioskStatus = ref<KioskStatus | null>(null);
const selectedKioskPlanId = ref<string>("");
const kioskLinkType = ref<"direct" | "ingress">("direct");
const showToken = ref(false);
const copySuccess = ref(false);
const tokenCopySuccess = ref(false);
const availablePlans = ref<Array<{ id: string; name: string }>>([]);

const computedKioskLink = computed(() => {
  const planPart = selectedKioskPlanId.value ? `/${selectedKioskPlanId.value}` : "";
  const token = kioskStatus.value?.kiosk_token || "";
  const tokenParam = token ? `?token=${encodeURIComponent(token)}` : "";

  if (kioskLinkType.value === "direct") {
    const host = window.location.hostname || "127.0.0.1";
    const port = kioskStatus.value?.kiosk_port || 8100;
    return `http://${host}:${port}/kiosk${planPart}${tokenParam}`;
  } else {
    const origin = window.location.origin;
    const basePath = getBasePath();
    return `${origin}${basePath}/#/kiosk${planPart}`;
  }
});

async function copyKioskLink() {
  try {
    await navigator.clipboard.writeText(computedKioskLink.value);
    copySuccess.value = true;
    setTimeout(() => {
      copySuccess.value = false;
    }, 2500);
  } catch (err) {
    console.error("Clipboard copy failed", err);
  }
}

async function copyKioskToken() {
  if (!kioskStatus.value?.kiosk_token) return;
  try {
    await navigator.clipboard.writeText(kioskStatus.value.kiosk_token);
    tokenCopySuccess.value = true;
    setTimeout(() => {
      tokenCopySuccess.value = false;
    }, 2500);
  } catch (err) {
    console.error("Token copy failed", err);
  }
}

function openKioskLink() {
  window.open(computedKioskLink.value, "_blank");
}

async function refreshKioskStatus() {
  try {
    const status = await api.getKioskStatus();
    kioskStatus.value = status;
  } catch (err) {
    console.error("Failed to refresh kiosk status", err);
  }
}

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
      if (props.initialTab) {
        activeTab.value = props.initialTab;
      }
      errorMessage.value = null;
      successMessage.value = null;
      syncResult.value = null;

      if (props.plans && props.plans.length > 0) {
        availablePlans.value = props.plans;
      } else {
        api.listPlans().then((res) => {
          availablePlans.value = res.plans;
        }).catch(() => {});
      }

      try {
        isLoading.value = true;
        const res = await api.getSettings();
        if (res.kiosk) {
          kioskStatus.value = res.kiosk;
        }

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

        const notifs = s.notifications || {};
        const em = notifs.email || {};
        emailHost.value = em.smtp_host || "";
        emailPort.value = em.smtp_port || 587;
        emailUser.value = em.smtp_user || "";
        emailPassword.value = em.smtp_password || "";
        emailFrom.value = em.smtp_from || "";
        emailDefaultTo.value = em.default_to || "";
        emailUseTls.value = em.smtp_use_tls ?? true;

        const wa = notifs.whatsapp || {};
        waProvider.value = wa.provider || "callmebot";
        waDefaultPhone.value = wa.default_phone || "";
        waApiKey.value = wa.api_key || "";
        waAccountSid.value = wa.account_sid || "";
        waFromPhone.value = wa.from_phone || "";

        if (s.dock_positions) {
          activityFeedDock.value = s.dock_positions.activity_feed || "bottom-left";
          navControlsDock.value = s.dock_positions.nav_controls || "bottom-right";
          toolbarDock.value = s.dock_positions.toolbar || "top";
          liveStore.setDockPositionsFromSettings(s.dock_positions);
          editorStore.setToolbarDock(toolbarDock.value);
        } else {
          activityFeedDock.value = liveStore.dockPositions.activity_feed;
          navControlsDock.value = liveStore.dockPositions.nav_controls;
          toolbarDock.value = editorStore.toolbarDock;
        }
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
      dock_positions: {
        activity_feed: activityFeedDock.value,
        nav_controls: navControlsDock.value,
        toolbar: toolbarDock.value,
      },
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
      notifications: {
        email: {
          smtp_host: emailHost.value.trim(),
          smtp_port: Number(emailPort.value),
          smtp_user: emailUser.value.trim(),
          smtp_password: emailPassword.value,
          smtp_from: emailFrom.value.trim(),
          default_to: emailDefaultTo.value.trim(),
          smtp_use_tls: emailUseTls.value,
        },
        whatsapp: {
          provider: waProvider.value,
          default_phone: waDefaultPhone.value.trim(),
          api_key: waApiKey.value.trim(),
          account_sid: waAccountSid.value.trim(),
          from_phone: waFromPhone.value.trim(),
        },
      },
    };

    const res = await api.saveSettings(payload);
    liveStore.setDockPosition("activity_feed", activityFeedDock.value);
    liveStore.setDockPosition("nav_controls", navControlsDock.value);
    editorStore.setToolbarDock(toolbarDock.value);
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
        <button
          type="button"
          class="nav-tab"
          :class="{ active: activeTab === 'notifications' }"
          @click="activeTab = 'notifications'"
        >
          <span class="tab-icon">🔔</span> Notification Defaults
        </button>
        <button
          type="button"
          class="nav-tab"
          :class="{ active: activeTab === 'kiosk' }"
          @click="activeTab = 'kiosk'"
        >
          <span class="tab-icon">🖥️</span> Kiosk & Share Links
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

            <!-- DOCKED MENUS & OVERLAY LAYOUT -->
            <div class="form-section">
              <div class="section-title-row">
                <div class="section-title">Docked Menus & Overlays Layout</div>
                <button
                  type="button"
                  class="reset-dock-btn"
                  @click="handleResetDockPositions"
                  title="Reset all docked menus to clean default corners"
                >
                  ↺ Reset Docked Positions
                </button>
              </div>
              <p class="section-desc">
                Choose which screen corners the Live Activity Feed and Navigation Controls dock to, preventing menu overlaps on desktop, tablets, and wall kiosks.
              </p>

              <div v-if="isDockOverlapping" class="alert-box warning">
                ⚠️ Both the Activity Feed and Navigation Controls are assigned to the <strong>{{ activityFeedDock }}</strong> corner. They may overlap. Consider placing them in separate corners (e.g. Activity Feed in Bottom Left, Controls in Bottom Right).
              </div>

              <div class="dock-options-grid">
                <!-- Activity Feed Card -->
                <div class="dock-config-card">
                  <div class="dock-card-header">
                    <span class="dock-card-icon">📋</span>
                    <div>
                      <div class="dock-card-title">Live Activity Feed</div>
                      <div class="dock-card-desc">Real-time sensor state events & alert drawer</div>
                    </div>
                  </div>
                  <div class="corner-picker">
                    <button
                      v-for="corner in cornerOptions"
                      :key="corner.value"
                      type="button"
                      class="corner-btn"
                      :class="{ active: activityFeedDock === corner.value }"
                      @click="activityFeedDock = corner.value"
                    >
                      <span class="corner-dot" :class="corner.value"></span>
                      {{ corner.label }}
                    </button>
                  </div>
                </div>

                <!-- Navigation Controls HUD Card -->
                <div class="dock-config-card">
                  <div class="dock-card-header">
                    <span class="dock-card-icon">🎮</span>
                    <div>
                      <div class="dock-card-title">TV & Navigation Controls HUD</div>
                      <div class="dock-card-desc">D-pad, zoom, center/fit, and position lock cluster</div>
                    </div>
                  </div>
                  <div class="corner-picker">
                    <button
                      v-for="corner in cornerOptions"
                      :key="corner.value"
                      type="button"
                      class="corner-btn"
                      :class="{ active: navControlsDock === corner.value }"
                      @click="navControlsDock = corner.value"
                    >
                      <span class="corner-dot" :class="corner.value"></span>
                      {{ corner.label }}
                    </button>
                  </div>
                </div>

                <!-- Editor Toolbar Docking Card -->
                <div class="dock-config-card" style="grid-column: 1 / -1;">
                  <div class="dock-card-header">
                    <span class="dock-card-icon">🛠️</span>
                    <div>
                      <div class="dock-card-title">Editor Drawing Toolbar</div>
                      <div class="dock-card-desc">Design mode toolbars (tools, drawing tools, undo, viewport simulators)</div>
                    </div>
                  </div>
                  <div class="corner-picker" style="grid-template-columns: repeat(4, 1fr);">
                    <button
                      v-for="tb in toolbarDockOptions"
                      :key="tb.value"
                      type="button"
                      class="corner-btn"
                      :class="{ active: toolbarDock === tb.value }"
                      @click="toolbarDock = tb.value"
                    >
                      <span class="corner-dot" :class="tb.value"></span>
                      {{ tb.label }}
                    </button>
                  </div>
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

          <!-- TAB 4: NOTIFICATION DEFAULTS (EMAIL & WHATSAPP) -->
          <div v-if="activeTab === 'notifications'" class="tab-content">
            <div class="form-section">
              <div class="section-title">Notification & Action Defaults</div>
              <p class="section-desc">
                Configure default credentials for expandable action plugins. When rules trigger, action plugins (Email, WhatsApp) will use these credentials automatically unless overridden.
              </p>

              <!-- Email (SMTP) Defaults -->
              <div class="notif-block">
                <div class="notif-block-header">
                  <span class="notif-icon">✉️</span>
                  <strong>Email (SMTP) Credentials</strong>
                </div>

                <div class="form-row">
                  <div class="form-group flex-2">
                    <label>SMTP Host</label>
                    <input v-model="emailHost" type="text" placeholder="smtp.gmail.com or mail.local" />
                  </div>
                  <div class="form-group flex-1">
                    <label>Port</label>
                    <input v-model.number="emailPort" type="number" placeholder="587" />
                  </div>
                </div>

                <div class="form-row">
                  <div class="form-group flex-1">
                    <label>Username</label>
                    <input v-model="emailUser" type="text" placeholder="alerts@mydomain.com" />
                  </div>
                  <div class="form-group flex-1">
                    <label>Password</label>
                    <input v-model="emailPassword" type="password" placeholder="••••••••" />
                  </div>
                </div>

                <div class="form-row">
                  <div class="form-group flex-1">
                    <label>From Address</label>
                    <input v-model="emailFrom" type="text" placeholder="security-hawk@mydomain.com" />
                  </div>
                  <div class="form-group flex-1">
                    <label>Default Recipient (To)</label>
                    <input v-model="emailDefaultTo" type="text" placeholder="admin@mydomain.com" />
                  </div>
                </div>

                <div class="form-group">
                  <label class="checkbox-label">
                    <input type="checkbox" v-model="emailUseTls" />
                    <span>Use TLS / STARTTLS Encryption (Default for Port 587)</span>
                  </label>
                </div>
              </div>

              <!-- WhatsApp Defaults -->
              <div class="notif-block">
                <div class="notif-block-header">
                  <span class="notif-icon">💬</span>
                  <strong>WhatsApp Messenger Defaults</strong>
                </div>

                <div class="form-row">
                  <div class="form-group flex-1">
                    <label>Provider</label>
                    <select v-model="waProvider">
                      <option value="callmebot">CallMeBot (Free & Simple for HA)</option>
                      <option value="custom_webhook">Custom Gateway / Webhook</option>
                      <option value="twilio">Twilio WhatsApp</option>
                    </select>
                  </div>
                  <div class="form-group flex-1">
                    <label>Default Recipient Phone</label>
                    <input v-model="waDefaultPhone" type="text" placeholder="+14155552671" />
                  </div>
                </div>

                <div class="form-group">
                  <label>API Key / Token</label>
                  <input v-model="waApiKey" type="password" placeholder="CallMeBot API Key or Twilio Auth Token" />
                  <span class="field-hint">
                    For CallMeBot, send WhatsApp message: <code>I allow callmebot to send me messages</code> to <code>+34 644 44 44 44</code> to receive your free key.
                  </span>
                </div>
              </div>
            </div>
          </div>

          <!-- TAB 5: KIOSK & SHARE LINKS -->
          <div v-if="activeTab === 'kiosk'" class="tab-content">
            <div class="form-section">
              <div class="section-title">🖥️ Wall Display & Kiosk Share Link</div>
              <p class="section-desc">
                Generate dedicated shareable links for wall tablets, smart TVs, or Fully Kiosk Browser. Kiosk mode provides a hardened, read-only interface displaying live sensor statuses without editing controls.
              </p>

              <!-- Live Active Viewers Telemetry Card -->
              <div class="viewers-telemetry-card">
                <div class="telemetry-header">
                  <div class="telemetry-title">
                    <span class="live-dot pulse"></span>
                    <span>Live Active Viewers</span>
                  </div>
                  <button type="button" class="btn-refresh-telemetry" @click="refreshKioskStatus" title="Refresh viewer count">
                    🔄 Refresh
                  </button>
                </div>
                <div class="telemetry-stats-grid">
                  <div class="stat-box primary">
                    <div class="stat-number">{{ kioskStatus?.active_viewers?.total_viewers ?? liveStore.totalViewers ?? 1 }}</div>
                    <div class="stat-label">Total Connected Screens</div>
                  </div>
                  <div class="stat-box">
                    <div class="stat-number">{{ kioskStatus?.active_viewers?.kiosk_viewers ?? 0 }}</div>
                    <div class="stat-label">🖥️ Kiosk Displays</div>
                  </div>
                  <div class="stat-box">
                    <div class="stat-number">{{ kioskStatus?.active_viewers?.standard_viewers ?? 1 }}</div>
                    <div class="stat-label">💻 Editor / Live Viewers</div>
                  </div>
                </div>
              </div>

              <!-- Link Generator Configuration -->
              <div class="kiosk-config-card">
                <div class="form-group">
                  <label>Select Floor Plan</label>
                  <select v-model="selectedKioskPlanId" class="form-select">
                    <option value="">Overview / Default (Auto-selects active building floor)</option>
                    <option v-for="plan in availablePlans" :key="plan.id" :value="plan.id">
                      {{ plan.name }}
                    </option>
                  </select>
                </div>

                <div class="form-group">
                  <label>Link Access Route</label>
                  <div class="route-selector">
                    <button
                      type="button"
                      class="route-btn"
                      :class="{ active: kioskLinkType === 'direct' }"
                      @click="kioskLinkType = 'direct'"
                    >
                      <span class="route-icon">📺</span>
                      <div class="route-details">
                        <span class="route-title">Direct Port 8100 Link (Recommended)</span>
                        <span class="route-subtitle">Standalone direct access for wall tablets, TVs, and tablets without HA login.</span>
                      </div>
                    </button>
                    <button
                      type="button"
                      class="route-btn"
                      :class="{ active: kioskLinkType === 'ingress' }"
                      @click="kioskLinkType = 'ingress'"
                    >
                      <span class="route-icon">🔒</span>
                      <div class="route-details">
                        <span class="route-title">Home Assistant Ingress Link</span>
                        <span class="route-subtitle">Internal kiosk route authenticated through your Home Assistant session.</span>
                      </div>
                    </button>
                  </div>
                </div>

                <!-- Share URL Display & Copy Actions -->
                <div class="form-group share-link-group">
                  <label>Shareable Kiosk URL</label>
                  <div class="url-input-container">
                    <input
                      type="text"
                      readonly
                      :value="computedKioskLink"
                      class="url-input"
                      @click="copyKioskLink"
                    />
                    <button
                      type="button"
                      class="btn-copy-url"
                      :class="{ copied: copySuccess }"
                      @click="copyKioskLink"
                    >
                      {{ copySuccess ? '✓ Copied!' : '📋 Copy Link' }}
                    </button>
                    <button
                      type="button"
                      class="btn-open-url"
                      @click="openKioskLink"
                      title="Open Kiosk View in new browser tab"
                    >
                      ↗️ Open
                    </button>
                  </div>
                </div>

                <!-- Port & Token Security Details -->
                <div class="kiosk-status-strip">
                  <div class="status-item">
                    <span class="status-label">Port 8100 Status:</span>
                    <span
                      class="status-badge"
                      :class="kioskStatus?.kiosk_enabled ? 'badge-success' : 'badge-warning'"
                    >
                      {{ kioskStatus?.kiosk_enabled ? '🟢 Enabled' : '🟡 Standby / Ingress' }}
                    </span>
                  </div>
                  <div v-if="kioskStatus?.kiosk_token" class="status-item token-item">
                    <span class="status-label">Security Token:</span>
                    <code class="token-code">
                      {{ showToken ? kioskStatus.kiosk_token : '••••••••••••••••••••••••' }}
                    </code>
                    <button
                      type="button"
                      class="btn-reveal"
                      @click="showToken = !showToken"
                      :title="showToken ? 'Hide token' : 'Reveal token'"
                    >
                      {{ showToken ? '🙈' : '👁️' }}
                    </button>
                    <button
                      type="button"
                      class="btn-copy-token"
                      @click="copyKioskToken"
                      title="Copy token to clipboard"
                    >
                      {{ tokenCopySuccess ? '✓' : '📋' }}
                    </button>
                  </div>
                </div>
              </div>

              <!-- Quick Device Setup Instructions -->
              <div class="device-tips-box">
                <div class="tips-title">💡 Wall Display & Tablet Setup Tips</div>
                <ul class="tips-list">
                  <li><strong>Fully Kiosk Browser (Android / Fire Tablet):</strong> Set the <em>Start URL</em> to the Direct Port 8100 link. Enable "Ignore SSL Warnings" and "Keep Screen On".</li>
                  <li><strong>iPad / iOS:</strong> Open the link in Safari, tap <em>Share &rarr; Add to Home Screen</em>, and enable <em>Guided Access</em> in iOS Settings for kiosk lockdown.</li>
                  <li><strong>Smart TVs & Raspberry Pi:</strong> Run Chromium in kiosk mode: <code>chromium-browser --kiosk --noerrdialogs "&lt;SHARE_URL&gt;"</code>.</li>
                </ul>
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

.notif-block {
  background: rgba(15, 23, 42, 0.45);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.notif-block-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--text-primary);
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  padding-bottom: 6px;
}

.notif-icon {
  font-size: 16px;
}

/* Kiosk & Share Links Styles */
.section-desc {
  font-size: 12px;
  color: var(--text-muted);
  line-height: 1.5;
  margin: 0 0 16px;
}

.viewers-telemetry-card {
  background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.8) 100%);
  border: 1px solid rgba(99, 102, 241, 0.25);
  border-radius: var(--radius-md);
  padding: 14px 16px;
  margin-bottom: 16px;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
}

.telemetry-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.telemetry-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 600;
  color: #c7d2fe;
}

.live-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #10b981;
}

.live-dot.pulse {
  animation: pulse-dot 1.8s infinite;
}

@keyframes pulse-dot {
  0% { transform: scale(0.9); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
  70% { transform: scale(1.1); box-shadow: 0 0 0 6px rgba(16, 185, 129, 0); }
  100% { transform: scale(0.9); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
}

.btn-refresh-telemetry {
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: var(--text-muted);
  font-size: 11px;
  padding: 3px 8px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all 0.2s;
}

.btn-refresh-telemetry:hover {
  background: rgba(255, 255, 255, 0.12);
  color: var(--text-primary);
}

.telemetry-stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}

.stat-box {
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: var(--radius-sm);
  padding: 10px;
  text-align: center;
}

.stat-box.primary {
  border-color: rgba(99, 102, 241, 0.35);
  background: rgba(99, 102, 241, 0.08);
}

.stat-number {
  font-size: 22px;
  font-weight: 700;
  color: #f8fafc;
  line-height: 1.2;
}

.stat-box.primary .stat-number {
  color: #818cf8;
}

.stat-label {
  font-size: 10px;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-top: 4px;
}

.kiosk-config-card {
  background: rgba(15, 23, 42, 0.45);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  margin-bottom: 16px;
}

.route-selector {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.route-btn {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 10px 12px;
  cursor: pointer;
  text-align: left;
  transition: all 0.2s;
}

.route-btn:hover {
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(99, 102, 241, 0.4);
}

.route-btn.active {
  background: rgba(99, 102, 241, 0.12);
  border-color: #6366f1;
}

.route-icon {
  font-size: 18px;
  margin-top: 2px;
}

.route-details {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.route-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary);
}

.route-subtitle {
  font-size: 10px;
  color: var(--text-muted);
  line-height: 1.3;
}

.share-link-group {
  margin-top: 2px;
}

.url-input-container {
  display: flex;
  gap: 8px;
  align-items: center;
}

.url-input {
  flex: 1;
  background: rgba(0, 0, 0, 0.4);
  border: 1px solid rgba(99, 102, 241, 0.3);
  color: #38bdf8;
  font-family: monospace;
  font-size: 11px;
  padding: 8px 10px;
  border-radius: var(--radius-sm);
  cursor: text;
}

.btn-copy-url {
  background: #6366f1;
  border: none;
  color: #ffffff;
  padding: 8px 14px;
  border-radius: var(--radius-sm);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.2s;
}

.btn-copy-url:hover {
  background: #4f46e5;
}

.btn-copy-url.copied {
  background: #10b981;
}

.btn-open-url {
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
  padding: 8px 12px;
  border-radius: var(--radius-sm);
  font-size: 12px;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.2s;
}

.btn-open-url:hover {
  background: rgba(255, 255, 255, 0.15);
}

.kiosk-status-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  align-items: center;
  padding-top: 8px;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  font-size: 11px;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.status-label {
  color: var(--text-muted);
}

.status-badge {
  padding: 2px 7px;
  border-radius: 10px;
  font-size: 10px;
  font-weight: 600;
}

.badge-success {
  background: rgba(16, 185, 129, 0.15);
  color: #34d399;
  border: 1px solid rgba(16, 185, 129, 0.3);
}

.badge-warning {
  background: rgba(245, 158, 11, 0.15);
  color: #fbbf24;
  border: 1px solid rgba(245, 158, 11, 0.3);
}

.token-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.token-code {
  background: rgba(0, 0, 0, 0.35);
  padding: 2px 6px;
  border-radius: var(--radius-sm);
  font-family: monospace;
  font-size: 10px;
  color: #e2e8f0;
}

.btn-reveal,
.btn-copy-token {
  background: transparent;
  border: none;
  cursor: pointer;
  font-size: 12px;
  padding: 2px 4px;
  border-radius: 4px;
  color: var(--text-muted);
  transition: all 0.2s;
}

.btn-reveal:hover,
.btn-copy-token:hover {
  color: var(--text-primary);
  background: rgba(255, 255, 255, 0.08);
}

.device-tips-box {
  background: rgba(30, 41, 59, 0.35);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: var(--radius-sm);
  padding: 12px 14px;
}

.tips-title {
  font-size: 11px;
  font-weight: 600;
  color: #cbd5e1;
  margin-bottom: 6px;
}

.tips-list {
  margin: 0;
  padding-left: 18px;
  font-size: 11px;
  color: var(--text-muted);
  line-height: 1.6;
}

.tips-list code {
  background: rgba(0, 0, 0, 0.3);
  padding: 1px 4px;
  border-radius: 3px;
  font-family: monospace;
  font-size: 10px;
  color: #93c5fd;
}

/* Docked Menus & Overlay Layout Styles */
.section-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 4px;
}

.reset-dock-btn {
  background: rgba(255, 255, 255, 0.07);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: var(--radius-sm, 6px);
  padding: 4px 10px;
  font-size: 11px;
  font-weight: 600;
  color: #a5b4fc;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  transition: all 0.15s ease;
}

.reset-dock-btn:hover {
  background: rgba(99, 102, 241, 0.25);
  border-color: #6366f1;
  color: #ffffff;
}

.dock-options-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
  margin-top: 12px;
}

@media (max-width: 640px) {
  .dock-options-grid {
    grid-template-columns: 1fr;
  }
}

.dock-config-card {
  background: rgba(30, 41, 59, 0.4);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: var(--radius-md, 8px);
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.dock-card-header {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}

.dock-card-icon {
  font-size: 20px;
}

.dock-card-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.dock-card-desc {
  font-size: 11px;
  color: var(--text-muted);
}

.corner-picker {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
}

.corner-btn {
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: var(--radius-sm, 6px);
  padding: 7px 10px;
  font-size: 11px;
  color: var(--text-secondary);
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: all 0.15s ease;
}

.corner-btn:hover {
  background: rgba(255, 255, 255, 0.08);
  color: #ffffff;
}

.corner-btn.active {
  background: rgba(99, 102, 241, 0.25);
  border-color: #6366f1;
  color: #ffffff;
  font-weight: 600;
}

.corner-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #64748b;
  display: inline-block;
}

.corner-btn.active .corner-dot {
  background: #6366f1;
  box-shadow: 0 0 6px rgba(99, 102, 241, 0.8);
}
</style>
