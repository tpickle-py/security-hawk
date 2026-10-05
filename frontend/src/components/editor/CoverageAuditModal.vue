<template>
  <Teleport to="body">
    <div v-if="show" class="audit-backdrop" @click.self="emit('close')">
      <div class="audit-modal glass-panel">
        <div class="audit-header">
          <div class="header-left">
            <span class="shield-icon" :class="auditData?.status === 'secure' ? 'secure' : 'warning'">
              {{ auditData?.status === 'secure' ? '🛡️' : '⚠️' }}
            </span>
            <div>
              <h3>Security Coverage & Gap Audit</h3>
              <p class="subtitle">AI & Rules validation engine analysis of your floor plan layout</p>
            </div>
          </div>
          <button class="btn-close" @click="emit('close')">✕</button>
        </div>

        <div class="audit-body">
          <div v-if="isLoading" class="audit-loading">
            <div class="spinner"></div>
            <span>Analyzing architectural layout and device coverage...</span>
          </div>

          <div v-else-if="error" class="audit-error">
            <p>{{ error }}</p>
            <button class="btn-retry" @click="runAudit">Retry Audit</button>
          </div>

          <div v-else-if="auditData" class="audit-content">
            <!-- Overall Status Banner -->
            <div class="status-banner" :class="auditData.status === 'secure' ? 'secure' : 'warning'">
              <div class="banner-icon">
                {{ auditData.status === 'secure' ? '✅' : '🔍' }}
              </div>
              <div>
                <h4>{{ auditData.status === 'secure' ? 'Full Security Coverage' : 'Coverage Gaps Identified' }}</h4>
                <p>
                  {{
                    auditData.status === 'secure'
                      ? 'All key entry points, rooms, and surveillance cones appear adequately covered on this floor.'
                      : `${auditData.recommendations.length} action item${auditData.recommendations.length === 1 ? '' : 's'} recommended to secure unmonitored areas.`
                  }}
                </p>
              </div>
            </div>

            <!-- Floor Plan Stats Grid -->
            <div class="stats-grid">
              <div class="stat-card">
                <span class="stat-num">{{ auditData.stats.rooms_count }}</span>
                <span class="stat-label">Rooms</span>
              </div>
              <div class="stat-card">
                <span class="stat-num">{{ auditData.stats.sub_areas_count }}</span>
                <span class="stat-label">Zones</span>
              </div>
              <div class="stat-card">
                <span class="stat-num">{{ auditData.stats.walls_count }}</span>
                <span class="stat-label">Walls</span>
              </div>
              <div class="stat-card">
                <span class="stat-num">{{ auditData.stats.door_cutouts_count }}</span>
                <span class="stat-label">Doors</span>
              </div>
              <div class="stat-card highlight">
                <span class="stat-num">{{ auditData.stats.total_sensors_placed }}</span>
                <span class="stat-label">Sensors</span>
              </div>
            </div>

            <!-- Recommendations & Gaps -->
            <div class="recommendations-section">
              <h5>Recommendations & Action Items</h5>
              <div v-if="auditData.recommendations.length === 0" class="no-gaps">
                <span>🎉 Excellent! No security blind spots or unmonitored portals detected.</span>
              </div>
              <ul v-else class="rec-list">
                <li v-for="(rec, idx) in auditData.recommendations" :key="idx" class="rec-item">
                  <span class="rec-bullet">⚠️</span>
                  <span>{{ rec }}</span>
                </li>
              </ul>
            </div>
          </div>
        </div>

        <div class="audit-footer">
          <button class="btn-refresh" @click="runAudit" :disabled="isLoading">
            🔄 Refresh Audit
          </button>
          <button class="btn-done" @click="emit('close')">
            Close
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, watch } from "vue";
import { usePlanStore } from "@/stores/planStore";

const props = defineProps<{
  show: boolean;
}>();

const emit = defineEmits<{
  (e: "close"): void;
}>();

const planStore = usePlanStore();

interface AuditStats {
  rooms_count: number;
  sub_areas_count: number;
  walls_count: number;
  door_cutouts_count: number;
  total_sensors_placed: number;
}

interface AuditResponse {
  plan_name: string;
  stats: AuditStats;
  recommendations: string[];
  status: "secure" | "action_recommended";
}

const auditData = ref<AuditResponse | null>(null);
const isLoading = ref(false);
const error = ref<string | null>(null);

async function runAudit() {
  isLoading.value = true;
  error.value = null;
  try {
    const res = await fetch("/api/mcp/execute", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        name: "validate_security_coverage",
        arguments: {
          plan_id: planStore.currentPlanId,
        },
      }),
    });
    if (!res.ok) {
      throw new Error(`Audit service returned HTTP ${res.status}`);
    }
    const data = await res.json();
    if (data.error) {
      throw new Error(data.error);
    }
    auditData.value = data;
  } catch (e: any) {
    error.value = e?.message || "Failed to run security coverage audit";
  } finally {
    isLoading.value = false;
  }
}

watch(
  () => props.show,
  (open) => {
    if (open) {
      runAudit();
    }
  },
  { immediate: true }
);
</script>

<style scoped>
.audit-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(4px);
  z-index: 10000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.audit-modal {
  background: #181920;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 12px;
  width: 100%;
  max-width: 620px;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.6);
  color: #e2e8f0;
  overflow: hidden;
}

.audit-header {
  padding: 16px 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.shield-icon {
  font-size: 24px;
  padding: 8px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.05);
}
.shield-icon.secure {
  background: rgba(16, 185, 129, 0.15);
}
.shield-icon.warning {
  background: rgba(245, 158, 11, 0.15);
}

.header-left h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #f8fafc;
}

.subtitle {
  margin: 2px 0 0;
  font-size: 12px;
  color: #94a3b8;
}

.btn-close {
  background: transparent;
  border: none;
  color: #94a3b8;
  font-size: 18px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
}
.btn-close:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
}

.audit-body {
  padding: 20px;
  overflow-y: auto;
  flex: 1;
}

.audit-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 40px 20px;
  color: #94a3b8;
  font-size: 13px;
}

.spinner {
  width: 28px;
  height: 28px;
  border: 3px solid rgba(99, 102, 241, 0.2);
  border-top-color: #6366f1;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.status-banner {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 8px;
  margin-bottom: 16px;
}
.status-banner.secure {
  background: rgba(16, 185, 129, 0.12);
  border: 1px solid rgba(16, 185, 129, 0.3);
}
.status-banner.warning {
  background: rgba(245, 158, 11, 0.12);
  border: 1px solid rgba(245, 158, 11, 0.3);
}

.banner-icon {
  font-size: 20px;
}

.status-banner h4 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: #f8fafc;
}

.status-banner p {
  margin: 4px 0 0;
  font-size: 12px;
  color: #cbd5e1;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 8px;
  margin-bottom: 20px;
}

.stat-card {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 8px;
  padding: 10px 8px;
  text-align: center;
  display: flex;
  flex-direction: column;
}
.stat-card.highlight {
  border-color: rgba(99, 102, 241, 0.4);
  background: rgba(99, 102, 241, 0.08);
}

.stat-num {
  font-size: 18px;
  font-weight: 700;
  color: #f1f5f9;
}

.stat-label {
  font-size: 10px;
  color: #94a3b8;
  margin-top: 2px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.recommendations-section h5 {
  margin: 0 0 10px;
  font-size: 13px;
  font-weight: 600;
  color: #cbd5e1;
}

.rec-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.rec-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 12px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 6px;
  font-size: 12px;
  color: #e2e8f0;
}

.rec-bullet {
  flex-shrink: 0;
}

.no-gaps {
  padding: 16px;
  text-align: center;
  background: rgba(16, 185, 129, 0.08);
  border-radius: 8px;
  font-size: 13px;
  color: #34d399;
}

.audit-footer {
  padding: 12px 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #14151b;
}

.btn-refresh {
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.15);
  color: #cbd5e1;
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
}
.btn-refresh:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.05);
}

.btn-done {
  background: #6366f1;
  border: none;
  color: #fff;
  padding: 6px 16px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
}
.btn-done:hover {
  background: #4f46e5;
}
</style>
