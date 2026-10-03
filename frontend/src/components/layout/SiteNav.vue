<script setup lang="ts">
import { ref } from "vue";
import { usePlanStore } from "@/stores/planStore";

const planStore = usePlanStore();
const showNewFloorInput = ref(false);
const newFloorName = ref("");

function handleAddFloor() {
  if (!newFloorName.value.trim() || !planStore.site) return;
  let b = planStore.currentBuilding;
  if (!b) {
    if (planStore.site.buildings.length === 0) {
      // Create default building
      const newBuilding = {
        id: "b_" + Math.random().toString(36).substring(2, 8),
        name: "Main Building",
        x: 100,
        y: 100,
        floors: [],
      };
      planStore.site.buildings.push(newBuilding);
      b = newBuilding;
    } else {
      b = planStore.site.buildings[0];
    }
  }

  const newFloor = {
    id: "fl_" + Math.random().toString(36).substring(2, 8),
    name: newFloorName.value.trim(),
    scale: null,
    background: null,
    shapes: [],
    endpoints: [],
  };

  b.floors.push(newFloor);
  planStore.selectBuildingFloor(b.id, newFloor.id);
  newFloorName.value = "";
  showNewFloorInput.value = false;
  planStore.savePlan();
}
</script>

<template>
  <nav class="site-nav" v-if="planStore.site">
    <!-- Overview Tab -->
    <button
      class="nav-tab"
      :class="{ active: planStore.isOverview }"
      @click="planStore.selectOverview"
    >
      <svg viewBox="0 0 24 24" width="14" height="14">
        <path fill="currentColor" d="M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8z"/>
      </svg>
      Overview
    </button>

    <!-- Buildings & Floors -->
    <div
      v-for="b in planStore.site.buildings"
      :key="b.id"
      class="building-group"
    >
      <div
        v-for="f in b.floors"
        :key="f.id"
        class="floor-tab-wrapper"
      >
        <button
          class="nav-tab"
          :class="{ active: planStore.currentFloorId === f.id && !planStore.isOverview }"
          @click="planStore.selectBuildingFloor(b.id, f.id)"
        >
          {{ b.floors.length > 1 ? `${b.name} - ${f.name}` : f.name }}
        </button>
      </div>
    </div>

    <!-- Add Floor prompt -->
    <div class="add-floor-wrapper">
      <button
        v-if="!showNewFloorInput"
        class="add-btn"
        title="Add new floor"
        @click="showNewFloorInput = true"
      >
        + Add Floor
      </button>
      <div v-else class="floor-input-box">
        <input
          type="text"
          v-model="newFloorName"
          placeholder="Floor name..."
          @keyup.enter="handleAddFloor"
          @keyup.esc="showNewFloorInput = false"
          autofocus
        />
        <button class="save-sm" @click="handleAddFloor">Add</button>
        <button class="cancel-sm" @click="showNewFloorInput = false">×</button>
      </div>
    </div>
  </nav>
</template>

<style scoped>
.site-nav {
  display: flex;
  align-items: center;
  gap: 4px;
  background: var(--bg-surface);
  padding: 3px 6px;
  border-radius: var(--radius-full);
  border: 1px solid var(--border-color);
}

.building-group {
  display: flex;
  gap: 4px;
}

.nav-tab {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 12px;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary);
  border-radius: var(--radius-full);
}

.nav-tab:hover {
  color: var(--text-primary);
}

.nav-tab.active {
  background: var(--bg-secondary);
  color: #ffffff;
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--border-color);
}

.add-btn {
  font-size: 11px;
  font-weight: 500;
  color: var(--text-muted);
  padding: 4px 8px;
  border-radius: var(--radius-full);
}

.add-btn:hover {
  color: var(--text-primary);
  background: rgba(255, 255, 255, 0.05);
}

.floor-input-box {
  display: flex;
  align-items: center;
  gap: 4px;
}

.floor-input-box input {
  padding: 2px 8px;
  font-size: 11px;
  width: 100px;
}

.save-sm {
  font-size: 11px;
  background: var(--accent-primary);
  color: #ffffff;
  padding: 2px 6px;
  border-radius: var(--radius-sm);
}

.cancel-sm {
  font-size: 14px;
  color: var(--text-muted);
  padding: 0 4px;
}
</style>
