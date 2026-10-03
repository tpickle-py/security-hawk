<script setup lang="ts">
import { useEditorStore } from "@/stores/editorStore";

const editorStore = useEditorStore();
</script>

<template>
  <div class="mode-toggle">
    <button
      class="toggle-btn"
      :class="{ active: editorStore.mode === 'design' }"
      @click="editorStore.setMode('design')"
    >
      <svg viewBox="0 0 24 24" width="14" height="14">
        <path fill="currentColor" d="M20.71,7.04C21.1,6.65 21.1,6 20.71,5.63L18.37,3.29C18,2.9 17.35,2.9 16.96,3.29L15.12,5.12L18.87,8.87M3,17.25V21H6.75L17.81,9.93L14.07,6.18L3,17.25Z"/>
      </svg>
      Design
    </button>
    <button
      class="toggle-btn"
      :class="{ active: editorStore.mode === 'usage' }"
      @click="editorStore.setMode('usage')"
    >
      <svg viewBox="0 0 24 24" width="14" height="14">
        <path fill="currentColor" d="M12,9A3,3 0 0,0 9,12A3,3 0 0,0 12,15A3,3 0 0,0 15,12A3,3 0 0,0 12,9M12,17A5,5 0 0,1 7,12A5,5 0 0,1 12,7A5,5 0 0,1 17,12A5,5 0 0,1 12,17M12,4.5C7,4.5 2.73,7.61 1,12C2.73,16.39 7,19.5 12,19.5C17,19.5 21.27,16.39 23,12C21.27,7.61 17,4.5 12,4.5Z"/>
      </svg>
      Live View
    </button>
  </div>
</template>

<style scoped>
.mode-toggle {
  display: flex;
  background: var(--bg-surface);
  padding: 3px;
  border-radius: var(--radius-full);
  border: 1px solid var(--border-color);
}

.toggle-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 12px;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary);
  border-radius: var(--radius-full);
}

.toggle-btn:hover {
  color: var(--text-primary);
}

.toggle-btn.active {
  background: var(--accent-primary);
  color: #ffffff;
  box-shadow: 0 0 10px var(--accent-primary-glow);
}
</style>
