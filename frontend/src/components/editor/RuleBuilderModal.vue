<script setup lang="ts">
import { ref, computed, watch } from "vue";
import type { CompositeRule, RuleCondition } from "@/types/plan";
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
const linkedCameras = ref<string[]>([]);
const hasServiceCall = ref(false);
const serviceDomain = ref("alarm_control_panel");
const serviceName = ref("alarm_trigger");
const serviceDataJson = ref("{}");

const isSaving = ref(false);
const isTesting = ref(false);
const testResult = ref<string | null>(null);
const errorMessage = ref<string | null>(null);

const availableCameras = computed(() => {
  return entityStore.entities.filter((e) => e.domain === "camera" || entityStore.guessEndpointType(e) === "camera");
});

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
  (isShowing) => {
    if (isShowing) {
      testResult.value = null;
      errorMessage.value = null;
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
        if (props.ruleToEdit.service_call) {
          hasServiceCall.value = true;
          serviceDomain.value = props.ruleToEdit.service_call.domain || "";
          serviceName.value = props.ruleToEdit.service_call.service || "";
          serviceDataJson.value = JSON.stringify(props.ruleToEdit.service_call.service_data || {}, null, 2);
        } else {
          hasServiceCall.value = false;
        }
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
        linkedCameras.value = [];
        hasServiceCall.value = false;
        serviceDomain.value = "alarm_control_panel";
        serviceName.value = "alarm_trigger";
        serviceDataJson.value = "{}";
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

  let serviceCallObj = undefined;
  if (hasServiceCall.value && serviceDomain.value && serviceName.value) {
    let parsedData = {};
    try {
      if (serviceDataJson.value.trim()) {
        parsedData = JSON.parse(serviceDataJson.value);
      }
    } catch {
      errorMessage.value = "Invalid JSON in service call parameters.";
      return;
    }
    serviceCallObj = {
      domain: serviceDomain.value.trim(),
      service: serviceName.value.trim(),
      service_data: parsedData,
    };
  }

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
    linked_cameras: linkedCameras.value,
    service_call: serviceCallObj,
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

          <!-- Optional HA Service Call -->
          <div class="service-call-section">
            <label class="checkbox-inline">
              <input type="checkbox" v-model="hasServiceCall" />
              <span>Call Home Assistant Service when triggered (e.g. alarm trigger, sirens, lights)</span>
            </label>

            <div v-if="hasServiceCall" class="service-fields">
              <div class="form-row">
                <div class="form-group flex-1">
                  <label>Domain</label>
                  <input v-model="serviceDomain" type="text" placeholder="alarm_control_panel" />
                </div>
                <div class="form-group flex-1">
                  <label>Service</label>
                  <input v-model="serviceName" type="text" placeholder="alarm_trigger" />
                </div>
              </div>
              <div class="form-group">
                <label>Service Data (JSON)</label>
                <textarea
                  v-model="serviceDataJson"
                  rows="2"
                  placeholder='{"code": "1234"}'
                  class="code-textarea"
                ></textarea>
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
</style>
