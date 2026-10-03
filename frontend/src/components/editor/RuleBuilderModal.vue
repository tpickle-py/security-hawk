<script setup lang="ts">
import { ref, computed, watch } from "vue";
import type { ActionPlugin, CompositeRule, RuleAction, RuleCondition } from "@/types/plan";
import { api } from "@/services/api";
import { useEntityStore } from "@/stores/entityStore";

const props = defineProps<{
  show: boolean;
  ruleToEdit?: CompositeRule | null;
}>();

const emit = defineEmits<{
  (e: "close"): void;
  (e: "saved", rule: CompositeRule): void;
}>();

const entityStore = useEntityStore();

const ruleId = ref("");
const name = ref("");
const enabled = ref(true);
const logic = ref<"ALL" | "ANY">("ALL");
const timeWindowSeconds = ref(30);
const resetSeconds = ref(60);
const deviceClass = ref("safety");
const outputEntityId = ref("");
const conditions = ref<RuleCondition[]>([]);
const actions = ref<RuleAction[]>([]);
const actionPlugins = ref<ActionPlugin[]>([]);
const selectedNewPlugin = ref("ha_service");
const linkedCameras = ref<string[]>([]);

const isSaving = ref(false);
const isTesting = ref(false);
const testResult = ref<string | null>(null);
const errorMessage = ref<string | null>(null);

const availableCameras = computed(() => {
  return entityStore.entities.filter((e) => e.domain === "camera" || entityStore.guessEndpointType(e) === "camera");
});

async function loadPlugins() {
  try {
    const res = await api.getActionPlugins();
    actionPlugins.value = res.plugins;
    if (res.plugins.length > 0 && !selectedNewPlugin.value) {
      selectedNewPlugin.value = res.plugins[0].type;
    }
  } catch (e) {
    console.error("Failed to load action plugins", e);
  }
}

function getPluginDef(type: string): ActionPlugin | undefined {
  return actionPlugins.value.find((p) => p.type === type);
}

function addAction(pluginType?: string) {
  const pType = pluginType || selectedNewPlugin.value || "ha_service";
  const plugin = getPluginDef(pType);
  const initialConfig: Record<string, any> = {};
  if (plugin) {
    for (const f of plugin.fields) {
      if (f.default !== undefined) {
        initialConfig[f.name] = f.default;
      }
    }
  }
  actions.value.push({
    id: `act_${Math.random().toString(36).substring(2, 9)}`,
    type: pType,
    config: initialConfig,
    enabled: true,
  });
}

function removeAction(index: number) {
  actions.value.splice(index, 1);
}

function onActionPluginChange(act: RuleAction, newType: string) {
  act.type = newType;
  const plugin = getPluginDef(newType);
  const newConfig: Record<string, any> = {};
  if (plugin) {
    for (const f of plugin.fields) {
      if (f.default !== undefined) {
        newConfig[f.name] = f.default;
      }
    }
  }
  act.config = newConfig;
}

function slugify(text: string): string {
  return text
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
}

function updateSlug() {
  if (!props.ruleToEdit && name.value) {
    outputEntityId.value = `binary_sensor.security_hawk_${slugify(name.value)}`;
  }
}

watch(
  () => props.show,
  async (isShowing) => {
    if (isShowing) {
      testResult.value = null;
      errorMessage.value = null;
      await loadPlugins();

      if (props.ruleToEdit) {
        ruleId.value = props.ruleToEdit.id;
        name.value = props.ruleToEdit.name;
        enabled.value = props.ruleToEdit.enabled ?? true;
        logic.value = props.ruleToEdit.logic || "ALL";
        timeWindowSeconds.value = props.ruleToEdit.time_window_seconds ?? 30;
        resetSeconds.value = props.ruleToEdit.reset_seconds ?? 60;
        deviceClass.value = props.ruleToEdit.device_class || "safety";
        outputEntityId.value = props.ruleToEdit.output_entity_id || "";
        conditions.value = JSON.parse(JSON.stringify(props.ruleToEdit.conditions || []));
        linkedCameras.value = [...(props.ruleToEdit.linked_cameras || [])];

        const existingActions: RuleAction[] = JSON.parse(JSON.stringify(props.ruleToEdit.actions || []));
        // Backwards compatibility with legacy service_call
        if (existingActions.length === 0 && props.ruleToEdit.service_call) {
          const sc = props.ruleToEdit.service_call;
          if (sc.domain && sc.service) {
            existingActions.push({
              id: `act_${Math.random().toString(36).substring(2, 9)}`,
              type: "ha_service",
              config: {
                domain: sc.domain,
                service: sc.service,
                data: sc.service_data || {},
              },
              enabled: true,
            });
          }
        }
        actions.value = existingActions;
      } else {
        ruleId.value = "";
        name.value = "";
        enabled.value = true;
        logic.value = "ALL";
        timeWindowSeconds.value = 30;
        resetSeconds.value = 60;
        deviceClass.value = "safety";
        outputEntityId.value = "";
        conditions.value = [
          { entity_id: "", state: "on" },
          { entity_id: "", state: "on" },
        ];
        actions.value = [];
        linkedCameras.value = [];
      }
    }
  },
  { immediate: true }
);

function addCondition() {
  conditions.value.push({ entity_id: "", state: "on" });
}

function removeCondition(index: number) {
  conditions.value.splice(index, 1);
}

async function handleSave() {
  if (!name.value.trim()) {
    errorMessage.value = "Please enter a rule name.";
    return;
  }
  if (conditions.value.length === 0) {
    errorMessage.value = "Please add at least one trigger condition.";
    return;
  }
  for (const c of conditions.value) {
    if (!c.entity_id) {
      errorMessage.value = "All conditions must have an entity selected.";
      return;
    }
  }

  // Format actions (parse JSON string inputs if user entered JSON string)
  const formattedActions = actions.value.map((act) => {
    const cleanConfig = { ...act.config };
    for (const [k, v] of Object.entries(cleanConfig)) {
      if (typeof v === "string" && (k === "data" || k === "payload" || k === "headers")) {
        try {
          if (v.trim().startsWith("{") || v.trim().startsWith("[")) {
            cleanConfig[k] = JSON.parse(v);
          }
        } catch {
          // Keep string if not valid json
        }
      }
    }
    return {
      id: act.id,
      type: act.type,
      config: cleanConfig,
      enabled: act.enabled !== false,
    };
  });

  const payload: Partial<CompositeRule> = {
    id: ruleId.value || undefined,
    name: name.value.trim(),
    enabled: enabled.value,
    logic: logic.value,
    time_window_seconds: Number(timeWindowSeconds.value),
    reset_seconds: Number(resetSeconds.value),
    device_class: deviceClass.value,
    output_entity_id: outputEntityId.value.trim() || undefined,
    conditions: conditions.value,
    actions: formattedActions,
    linked_cameras: linkedCameras.value,
  };

  try {
    isSaving.value = true;
    errorMessage.value = null;
    const res = await api.saveRule(payload);
    emit("saved", res.rule);
    emit("close");
  } catch (err: any) {
    errorMessage.value = err.message || "Failed to save rule.";
  } finally {
    isSaving.value = false;
  }
}

async function handleTest() {
  if (!ruleId.value) {
    errorMessage.value = "Please save the rule first before running a live test.";
    return;
  }
  try {
    isTesting.value = true;
    testResult.value = null;
    errorMessage.value = null;
    const res = await api.testRule(ruleId.value);
    testResult.value = res.triggered ? "Rule triggered successfully! State published to HA & MQTT." : "Test executed.";
  } catch (err: any) {
    errorMessage.value = err.message || "Failed to test rule.";
  } finally {
    isTesting.value = false;
  }
}
</script>

<template>
  <div v-if="show" class="modal-backdrop" @click.self="emit('close')">
    <div class="rule-modal glass-panel">
      <!-- Modal Header -->
      <div class="modal-header">
        <div class="header-info">
          <div class="title-row">
            <span class="shield-badge">⚡</span>
            <h2>{{ ruleToEdit ? 'Edit Compound Rule' : 'New Compound Rule & Synthetic Sensor' }}</h2>
          </div>
          <p class="subtitle">
            Correlate multiple physical sensors (e.g. motion + camera + alarm state) to create a native Home Assistant synthetic sensor.
          </p>
        </div>
        <button class="close-btn" @click="emit('close')">✕</button>
      </div>

      <!-- Modal Body -->
      <div class="modal-body">
        <div v-if="errorMessage" class="alert-box error">
          {{ errorMessage }}
        </div>
        <div v-if="testResult" class="alert-box success">
          {{ testResult }}
        </div>

        <!-- Section: General Settings -->
        <div class="form-section">
          <div class="section-title">General Settings</div>
          <div class="form-row">
            <div class="form-group flex-2">
              <label>Rule Name</label>
              <input
                v-model="name"
                type="text"
                placeholder="e.g. Backyard Perimeter Intrusion"
                @input="updateSlug"
              />
            </div>
            <div class="form-group flex-1">
              <label>Status</label>
              <div class="toggle-pill-group">
                <button
                  type="button"
                  class="toggle-pill"
                  :class="{ active: enabled }"
                  @click="enabled = true"
                >
                  Enabled
                </button>
                <button
                  type="button"
                  class="toggle-pill"
                  :class="{ active: !enabled }"
                  @click="enabled = false"
                >
                  Disabled
                </button>
              </div>
            </div>
          </div>

          <div class="form-row">
            <div class="form-group flex-2">
              <label>Home Assistant Synthetic Entity ID</label>
              <input
                v-model="outputEntityId"
                type="text"
                placeholder="binary_sensor.security_hawk_backyard_perimeter"
              />
              <span class="field-hint">Published directly to Home Assistant's state machine & MQTT.</span>
            </div>
            <div class="form-group flex-1">
              <label>Device Class</label>
              <select v-model="deviceClass">
                <option value="safety">safety</option>
                <option value="motion">motion</option>
                <option value="door">door</option>
                <option value="window">window</option>
                <option value="problem">problem</option>
                <option value="smoke">smoke</option>
                <option value="presence">presence</option>
              </select>
            </div>
          </div>
        </div>

        <!-- Section: Logic & Correlation Window -->
        <div class="form-section">
          <div class="section-title">Trigger Logic & Correlation Window</div>
          <div class="form-row">
            <div class="form-group flex-1">
              <label>Condition Matching Logic</label>
              <div class="toggle-pill-group">
                <button
                  type="button"
                  class="toggle-pill"
                  :class="{ active: logic === 'ALL' }"
                  @click="logic = 'ALL'"
                >
                  ALL (AND) — All conditions must match
                </button>
                <button
                  type="button"
                  class="toggle-pill"
                  :class="{ active: logic === 'ANY' }"
                  @click="logic = 'ANY'"
                >
                  ANY (OR) — Any condition matches
                </button>
              </div>
            </div>
          </div>

          <div class="form-row">
            <div class="form-group flex-1">
              <label>Time Correlation Window (seconds)</label>
              <div class="slider-val-row">
                <input
                  v-model.number="timeWindowSeconds"
                  type="range"
                  min="5"
                  max="300"
                  step="5"
                />
                <span class="val-badge">{{ timeWindowSeconds }}s</span>
              </div>
              <span class="field-hint">Events must occur within this window to correlate.</span>
            </div>

            <div class="form-group flex-1">
              <label>Auto-Reset to 'off' (seconds)</label>
              <div class="slider-val-row">
                <input
                  v-model.number="resetSeconds"
                  type="range"
                  min="10"
                  max="600"
                  step="10"
                />
                <span class="val-badge">{{ resetSeconds }}s</span>
              </div>
              <span class="field-hint">Automatically clears sensor back to off after this timeout.</span>
            </div>
          </div>
        </div>

        <!-- Section: Conditions (IF...) -->
        <div class="form-section">
          <div class="section-title-row">
            <div class="section-title">Trigger Conditions (IF...)</div>
            <button type="button" class="btn-sm btn-secondary" @click="addCondition">
              + Add Condition
            </button>
          </div>

          <div class="conditions-list">
            <div
              v-for="(cond, idx) in conditions"
              :key="idx"
              class="condition-row"
            >
              <span class="cond-badge">{{ logic === 'ALL' && idx > 0 ? 'AND' : logic === 'ANY' && idx > 0 ? 'OR' : 'IF' }}</span>

              <div class="cond-entity">
                <input
                  v-model="cond.entity_id"
                  type="text"
                  list="entity-list-suggestions"
                  placeholder="Select or enter entity_id (e.g. binary_sensor.backyard_motion)"
                />
              </div>

              <div class="cond-op">is state</div>

              <div class="cond-state">
                <select v-model="cond.state">
                  <option value="on">on / active / open</option>
                  <option value="off">off / clear / closed</option>
                  <option value="detected">detected</option>
                  <option value="armed_home">armed_home</option>
                  <option value="armed_away">armed_away</option>
                  <option value="triggered">triggered</option>
                </select>
              </div>

              <button
                type="button"
                class="remove-cond-btn"
                title="Remove condition"
                @click="removeCondition(idx)"
              >
                ✕
              </button>
            </div>
          </div>

          <datalist id="entity-list-suggestions">
            <option
              v-for="e in entityStore.entities"
              :key="e.entity_id"
              :value="e.entity_id"
            >
              {{ e.friendly_name || e.name }} ({{ e.entity_id }})
            </option>
          </datalist>
        </div>

        <!-- Section: Actions & Linked Cameras (THEN...) -->
        <div class="form-section">
          <div class="section-title">Outputs & Actions (THEN...)</div>

          <!-- Camera popups -->
          <div class="form-group">
            <label>Linked Camera Feed (Auto-Popup on Live View)</label>
            <div class="camera-checkbox-grid">
              <label
                v-for="cam in availableCameras"
                :key="cam.entity_id"
                class="cam-checkbox-label"
              >
                <input
                  type="checkbox"
                  :value="cam.entity_id"
                  v-model="linkedCameras"
                />
                <span>{{ cam.friendly_name || cam.entity_id }}</span>
              </label>
              <div v-if="availableCameras.length === 0" class="muted-text">
                No camera entities detected in Home Assistant.
              </div>
            </div>
          </div>

          <!-- Expandable Action Plugins (THEN...) -->
          <div class="actions-section">
            <div class="section-title-row">
              <div class="section-title">Automations & Notification Actions</div>
              <div class="add-action-controls">
                <select v-model="selectedNewPlugin" class="plugin-select-dropdown">
                  <option v-for="p in actionPlugins" :key="p.type" :value="p.type">
                    {{ p.name }}
                  </option>
                </select>
                <button type="button" class="btn-sm btn-secondary" @click="addAction()">
                  + Add Action
                </button>
              </div>
            </div>

            <div v-if="actions.length === 0" class="empty-actions-box">
              <span>No notification actions configured. The synthetic sensor state and live camera popup will still trigger. Add an action above to send Email, WhatsApp messages, call Home Assistant services, or trigger webhooks.</span>
            </div>

            <div v-else class="actions-list">
              <div
                v-for="(act, actIdx) in actions"
                :key="act.id || actIdx"
                class="action-card"
                :class="{ disabled: act.enabled === false }"
              >
                <!-- Action Card Header -->
                <div class="action-card-header">
                  <div class="action-header-left">
                    <span class="action-icon">
                      {{ act.type === 'ha_service' ? '🏠' : act.type === 'email' ? '✉️' : act.type === 'whatsapp' ? '💬' : '🌐' }}
                    </span>
                    <select
                      :value="act.type"
                      class="action-type-select"
                      @change="onActionPluginChange(act, ($event.target as HTMLSelectElement).value)"
                    >
                      <option v-for="p in actionPlugins" :key="p.type" :value="p.type">
                        {{ p.name }}
                      </option>
                    </select>
                  </div>
                  <div class="action-header-right">
                    <label class="toggle-switch-sm">
                      <input type="checkbox" v-model="act.enabled" />
                      <span class="switch-label">{{ act.enabled !== false ? 'Enabled' : 'Disabled' }}</span>
                    </label>
                    <button
                      type="button"
                      class="remove-cond-btn"
                      title="Remove action"
                      @click="removeAction(actIdx)"
                    >
                      ✕
                    </button>
                  </div>
                </div>

                <!-- Action Dynamic Fields -->
                <div class="action-card-body" v-if="getPluginDef(act.type)">
                  <div
                    v-for="field in getPluginDef(act.type)!.fields"
                    :key="field.name"
                    class="form-group"
                  >
                    <label>
                      {{ field.label }}
                      <span v-if="field.required" class="required-star">*</span>
                    </label>

                    <!-- Text / Password -->
                    <input
                      v-if="field.type === 'text' || field.type === 'password'"
                      :type="field.type"
                      v-model="act.config[field.name]"
                      :placeholder="field.placeholder"
                    />

                    <!-- Number -->
                    <input
                      v-else-if="field.type === 'number'"
                      type="number"
                      v-model.number="act.config[field.name]"
                      :placeholder="field.placeholder"
                    />

                    <!-- Select -->
                    <select
                      v-else-if="field.type === 'select'"
                      v-model="act.config[field.name]"
                    >
                      <option
                        v-for="opt in field.options"
                        :key="opt.value"
                        :value="opt.value"
                      >
                        {{ opt.label }}
                      </option>
                    </select>

                    <!-- Textarea -->
                    <textarea
                      v-else-if="field.type === 'textarea'"
                      rows="2"
                      v-model="act.config[field.name]"
                      :placeholder="field.placeholder"
                    ></textarea>

                    <!-- JSON -->
                    <textarea
                      v-else-if="field.type === 'json'"
                      rows="2"
                      :value="typeof act.config[field.name] === 'object' ? JSON.stringify(act.config[field.name], null, 2) : act.config[field.name]"
                      @input="act.config[field.name] = ($event.target as HTMLTextAreaElement).value"
                      :placeholder="field.placeholder"
                      class="code-textarea"
                    ></textarea>
                  </div>
                  <div class="template-hint">
                    💡 Supports template variables: <code>{rule_name}</code>, <code>{entities}</code>, <code>{output_entity_id}</code>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Modal Footer -->
      <div class="modal-footer">
        <div class="footer-left">
          <button
            v-if="ruleId"
            type="button"
            class="btn-test"
            :disabled="isTesting"
            @click="handleTest"
          >
            {{ isTesting ? 'Testing...' : '⚡ Test Trigger Now' }}
          </button>
        </div>
        <div class="footer-right">
          <button type="button" class="btn-secondary" @click="emit('close')">
            Cancel
          </button>
          <button
            type="button"
            class="btn-primary"
            :disabled="isSaving"
            @click="handleSave"
          >
            {{ isSaving ? 'Saving...' : 'Save Rule & Publish' }}
          </button>
        </div>
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

.rule-modal {
  width: 100%;
  max-width: 780px;
  max-height: 90vh;
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

.shield-badge {
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

.modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.alert-box {
  padding: 10px 14px;
  border-radius: var(--radius-sm);
  font-size: 13px;
  font-weight: 500;
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
  gap: 12px;
  padding-bottom: 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.section-title {
  font-size: 13px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--accent-primary);
}

.section-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
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
  padding: 6px 10px;
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

.slider-val-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.slider-val-row input[type="range"] {
  flex: 1;
}

.val-badge {
  background: rgba(99, 102, 241, 0.2);
  color: var(--accent-primary);
  font-size: 12px;
  font-weight: 600;
  padding: 3px 8px;
  border-radius: var(--radius-sm);
  min-width: 44px;
  text-align: center;
}

.conditions-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.condition-row {
  display: flex;
  align-items: center;
  gap: 10px;
  background: rgba(15, 23, 42, 0.5);
  border: 1px solid var(--border-color);
  padding: 8px 12px;
  border-radius: var(--radius-sm);
}

.cond-badge {
  font-size: 11px;
  font-weight: 700;
  color: var(--accent-primary);
  width: 32px;
}

.cond-entity {
  flex: 3;
}

.cond-op {
  font-size: 12px;
  color: var(--text-muted);
}

.cond-state {
  flex: 2;
}

.remove-cond-btn {
  background: transparent;
  border: none;
  color: var(--text-muted);
  font-size: 14px;
  cursor: pointer;
  padding: 4px 6px;
  border-radius: var(--radius-sm);
}

.remove-cond-btn:hover {
  color: var(--color-danger);
  background: rgba(239, 68, 68, 0.1);
}

.camera-checkbox-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 8px;
  max-height: 120px;
  overflow-y: auto;
  background: rgba(15, 23, 42, 0.5);
  padding: 8px 12px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-color);
}

.cam-checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--text-secondary);
  cursor: pointer;
}

.service-call-section {
  background: rgba(15, 23, 42, 0.5);
  border: 1px solid var(--border-color);
  padding: 12px;
  border-radius: var(--radius-sm);
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.checkbox-inline {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-primary);
  cursor: pointer;
}

.service-fields {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding-top: 8px;
  border-top: 1px dashed rgba(255, 255, 255, 0.1);
}

.code-textarea {
  font-family: monospace;
  font-size: 12px;
  background: rgba(0, 0, 0, 0.3);
}

.modal-footer {
  padding: 16px 20px;
  border-top: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.footer-right {
  display: flex;
  gap: 10px;
}

.btn-test {
  background: rgba(139, 92, 246, 0.2);
  border: 1px solid #8b5cf6;
  color: #c4b5fd;
  padding: 7px 14px;
  border-radius: var(--radius-sm);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-test:hover:not(:disabled) {
  background: rgba(139, 92, 246, 0.35);
  color: #ffffff;
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

.btn-sm {
  padding: 4px 10px;
  font-size: 11px;
}

.muted-text {
  font-size: 11px;
  color: var(--text-muted);
}

.actions-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 10px;
}

.add-action-controls {
  display: flex;
  align-items: center;
  gap: 8px;
}

.plugin-select-dropdown {
  font-size: 12px;
  padding: 4px 8px;
  background: rgba(15, 23, 42, 0.7);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
  border-radius: var(--radius-sm);
}

.empty-actions-box {
  background: rgba(15, 23, 42, 0.4);
  border: 1px dashed rgba(255, 255, 255, 0.15);
  padding: 14px;
  border-radius: var(--radius-sm);
  font-size: 12px;
  color: var(--text-muted);
  line-height: 1.4;
}

.actions-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.action-card {
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid var(--border-color);
  border-left: 3px solid var(--accent-primary);
  border-radius: var(--radius-sm);
  overflow: hidden;
  transition: all 0.15s ease;
}

.action-card.disabled {
  opacity: 0.6;
  border-left-color: #64748b;
}

.action-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background: rgba(30, 41, 59, 0.5);
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.action-header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.action-icon {
  font-size: 15px;
}

.action-type-select {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary);
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: var(--radius-sm);
  padding: 2px 6px;
}

.action-header-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.toggle-switch-sm {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
}

.switch-label {
  font-size: 11px;
  color: var(--text-secondary);
}

.action-card-body {
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.required-star {
  color: var(--color-danger);
  margin-left: 2px;
}

.template-hint {
  font-size: 11px;
  color: var(--text-muted);
  background: rgba(0, 0, 0, 0.2);
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  margin-top: 2px;
}

.template-hint code {
  color: #a5b4fc;
  background: rgba(99, 102, 241, 0.15);
  padding: 1px 4px;
  border-radius: 2px;
}
</style>
