<script setup lang="ts">
import { api } from "@/services/api";

const props = defineProps<{
  planId: string;
}>();

const emit = defineEmits<{
  (e: "close"): void;
}>();

function downloadJson() {
  const url = api.getExportUrl(props.planId);
  window.open(url, "_blank");
  emit("close");
}

function downloadBundle() {
  const url = api.getPlanBundleExportUrl(props.planId);
  window.open(url, "_blank");
  emit("close");
}
</script>

<template>
  <div class="modal-backdrop" @click.self="emit('close')">
    <div class="modal-card glass-panel">
      <div class="modal-header">
        <div class="title-with-icon">
          <span class="icon">📦</span>
          <h3>Export Floor Plan</h3>
        </div>
        <button class="close-btn" @click="emit('close')">✕</button>
      </div>

      <div class="modal-body">
        <!-- Privacy Notice required by Spec -->
        <div class="privacy-warning">
          <div class="warning-icon">⚠️</div>
          <div class="warning-text">
            <strong>Security & Privacy Notice</strong>
            <p>
              A shared plan bundle contains the layout of a building and where its sensors are.
              Only share exported files with trusted individuals, as sensor coordinates and floor plans expose physical security contours.
            </p>
          </div>
        </div>

        <div class="export-options">
          <!-- Bundle (.zip) -->
          <div class="export-card featured">
            <div class="card-badge">Complete Package</div>
            <div class="card-icon">🗜️</div>
            <div class="card-info">
              <h4>Plan Archive Bundle (.zip)</h4>
              <p>Contains <code>plan.json</code> plus all background floor plan images and blueprints under <code>assets/</code>. Ideal for complete migrations and backups.</p>
            </div>
            <button class="download-btn primary" @click="downloadBundle">
              <svg viewBox="0 0 24 24" width="16" height="16">
                <path fill="currentColor" d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/>
              </svg>
              <span>Download .zip Bundle</span>
            </button>
          </div>

          <!-- JSON only -->
          <div class="export-card">
            <div class="card-icon">📄</div>
            <div class="card-info">
              <h4>Plan Definition (.json)</h4>
              <p>Export only the geometric definitions, sensor coordinates, and settings. Background images remain referenced by filename.</p>
            </div>
            <button class="download-btn secondary" @click="downloadJson">
              <svg viewBox="0 0 24 24" width="16" height="16">
                <path fill="currentColor" d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/>
              </svg>
              <span>Download .json</span>
            </button>
          </div>
        </div>
      </div>

      <div class="modal-footer">
        <button class="cancel-btn" @click="emit('close')">Close</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.65);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  animation: fadeIn 0.15s ease-out;
}

.modal-card {
  width: 90%;
  max-width: 580px;
  background: var(--bg-surface, #1e293b);
  border: 1px solid var(--border-color, rgba(255, 255, 255, 0.1));
  border-radius: var(--radius-lg, 12px);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.5);
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color, rgba(255, 255, 255, 0.1));
}

.title-with-icon {
  display: flex;
  align-items: center;
  gap: 10px;
}

.title-with-icon .icon {
  font-size: 20px;
}

.title-with-icon h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary, #fff);
}

.close-btn {
  background: none;
  border: none;
  color: var(--text-muted, #94a3b8);
  font-size: 18px;
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
}

.close-btn:hover {
  color: var(--text-primary, #fff);
  background: rgba(255, 255, 255, 0.1);
}

.modal-body {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.privacy-warning {
  display: flex;
  gap: 12px;
  padding: 12px 14px;
  border-radius: 8px;
  background: rgba(245, 158, 11, 0.12);
  border: 1px solid rgba(245, 158, 11, 0.35);
  color: #fcd34d;
}

.warning-icon {
  font-size: 18px;
  flex-shrink: 0;
}

.warning-text strong {
  display: block;
  font-size: 13px;
  margin-bottom: 4px;
  color: #fbbf24;
}

.warning-text p {
  margin: 0;
  font-size: 12px;
  line-height: 1.45;
  color: #fef3c7;
}

.export-options {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.export-card {
  position: relative;
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 14px 16px;
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid var(--border-color, rgba(255, 255, 255, 0.08));
  border-radius: 8px;
  transition: all 0.2s ease;
}

.export-card.featured {
  border-color: rgba(99, 102, 241, 0.4);
  background: rgba(99, 102, 241, 0.05);
}

.card-badge {
  position: absolute;
  top: -9px;
  right: 14px;
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  padding: 2px 8px;
  background: #6366f1;
  color: white;
  border-radius: 999px;
}

.card-icon {
  font-size: 24px;
  flex-shrink: 0;
}

.card-info {
  flex: 1;
}

.card-info h4 {
  margin: 0 0 4px 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary, #fff);
}

.card-info p {
  margin: 0;
  font-size: 12px;
  color: var(--text-secondary, #94a3b8);
  line-height: 1.4;
}

.card-info code {
  background: rgba(0, 0, 0, 0.3);
  padding: 1px 4px;
  border-radius: 3px;
  font-family: var(--font-mono, monospace);
  font-size: 11px;
}

.download-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.15s ease;
  border: 1px solid transparent;
}

.download-btn.primary {
  background: #6366f1;
  color: #ffffff;
}

.download-btn.primary:hover {
  background: #4f46e5;
  box-shadow: 0 0 12px rgba(99, 102, 241, 0.4);
}

.download-btn.secondary {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(255, 255, 255, 0.15);
  color: var(--text-primary, #fff);
}

.download-btn.secondary:hover {
  background: rgba(255, 255, 255, 0.15);
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  padding: 12px 20px;
  border-top: 1px solid var(--border-color, rgba(255, 255, 255, 0.1));
}

.cancel-btn {
  padding: 6px 14px;
  background: transparent;
  border: 1px solid var(--border-color, rgba(255, 255, 255, 0.1));
  color: var(--text-secondary, #94a3b8);
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
}

.cancel-btn:hover {
  background: rgba(255, 255, 255, 0.05);
  color: var(--text-primary, #fff);
}

@keyframes fadeIn {
  from { opacity: 0; transform: scale(0.98); }
  to { opacity: 1; transform: scale(1); }
}
</style>
