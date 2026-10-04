<script setup lang="ts">
import { ref, computed } from "vue";
import { useLiveStore, type LiveEvent } from "@/stores/liveStore";
import { usePlanStore } from "@/stores/planStore";
import { useEditorStore } from "@/stores/editorStore";

const liveStore = useLiveStore();
const planStore = usePlanStore();
const editorStore = useEditorStore();

const isOpen = ref(false);
const searchQuery = ref("");

const filteredEvents = computed(() => {
  const q = searchQuery.value.trim().toLowerCase();
  if (!q) return liveStore.eventFeed;
  return liveStore.eventFeed.filter(
    (ev) =>
      ev.entity_id.toLowerCase().includes(q) ||
      (ev.friendly_name && ev.friendly_name.toLowerCase().includes(q)) ||
      ev.to_state?.toLowerCase().includes(q)
  );
});

const dockCorner = computed(() => liveStore.dockPositions?.activity_feed || "bottom-left");

const dockCornerLabel = computed(() => {
  switch (dockCorner.value) {
    case "bottom-left":
      return "Bottom Left";
    case "bottom-right":
      return "Bottom Right";
    case "top-left":
      return "Top Left";
    case "top-right":
      return "Top Right";
    default:
      return dockCorner.value;
  }
});

function cycleDock() {
  liveStore.cycleDockPosition("activity_feed");
}

function toggleOpen() {
  isOpen.value = !isOpen.value;
}

function formatTime(date: Date): string {
  const d = new Date(date);
  return d.toTimeString().split(" ")[0];
}

function handleEventClick(event: LiveEvent) {
  // Find endpoint associated with event's entity_id
  let foundFloorId: string | null = null;
  let foundBuildingId: string | null = null;
  let targetEp: any = null;

  // Check overview
  if (planStore.site?.overview.endpoints) {
    targetEp = planStore.site.overview.endpoints.find((ep) => ep.entity_id === event.entity_id);
    if (targetEp) {
      foundBuildingId = null;
      foundFloorId = null;
    }
  }

  // Check buildings and floors
  if (!targetEp && planStore.site?.buildings) {
    for (const b of planStore.site.buildings) {
      for (const f of b.floors) {
        targetEp = f.endpoints.find((ep) => ep.entity_id === event.entity_id);
        if (targetEp) {
          foundBuildingId = b.id;
          foundFloorId = f.id;
          break;
        }
      }
      if (targetEp) break;
    }
  }

  if (targetEp) {
    // Switch to target building/floor if needed
    if (foundBuildingId && foundFloorId) {
      planStore.selectBuildingFloor(foundBuildingId, foundFloorId);
    } else if (foundBuildingId === null && foundFloorId === null) {
      planStore.selectOverview();
    }

    // Pan canvas to center endpoint
    editorStore.panX = -targetEp.x * editorStore.zoom + window.innerWidth / 2;
    editorStore.panY = -targetEp.y * editorStore.zoom + window.innerHeight / 2;

    // Highlight endpoint
    liveStore.highlightEndpoint(targetEp.id);
  }
}
</script>

<template>
  <div class="event-feed-drawer" :class="[`dock-${dockCorner}`, { open: isOpen }]">
    <!-- Header / Toggle Tab -->
    <div class="drawer-header" @click="toggleOpen">
      <div class="header-left">
        <svg viewBox="0 0 24 24" width="16" height="16">
          <path fill="currentColor" d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zm-1 9V3.5L18.5 9H13zM4 20V4h7v6h6v10H4z"/>
        </svg>
        <span class="drawer-title">Live Activity Feed</span>
        <span class="event-count">{{ liveStore.eventFeed.length }}</span>
      </div>
      <div class="header-actions">
        <button
          class="dock-btn"
          type="button"
          :title="`Docked: ${dockCornerLabel}. Click to cycle corner position`"
          @click.stop="cycleDock"
        >
          <span class="dock-icon">⚓</span>
        </button>
        <button class="toggle-btn" :title="isOpen ? 'Collapse Feed' : 'Expand Feed'">
          <svg viewBox="0 0 24 24" width="14" height="14" :transform="isOpen ? 'rotate(180)' : undefined">
            <path fill="currentColor" d="M7.41 8.59L12 13.17l4.59-4.58L18 10l-6 6-6-6 1.41-1.41z"/>
          </svg>
        </button>
      </div>
    </div>

    <!-- Drawer Content -->
    <div class="drawer-content" v-if="isOpen">
      <div class="drawer-search">
        <input
          type="text"
          v-model="searchQuery"
          placeholder="Filter live events..."
        />
        <button
          v-if="liveStore.eventFeed.length > 0"
          class="clear-feed-btn"
          title="Clear Feed"
          @click="liveStore.eventFeed = []"
        >
          Clear
        </button>
      </div>

      <div class="events-scrollable">
        <div v-if="filteredEvents.length === 0" class="empty-feed">
          No recent activity recorded
        </div>
        <div
          v-for="ev in filteredEvents"
          :key="ev.id"
          class="event-item"
          @click="handleEventClick(ev)"
          title="Click to jump to endpoint"
        >
          <div class="event-time">{{ formatTime(ev.timestamp) }}</div>
          <div class="event-body">
            <div class="event-name">{{ ev.friendly_name || ev.entity_id }}</div>
            <div class="event-state">
              <span v-if="ev.from_state" class="state-pill from">{{ ev.from_state }}</span>
              <span v-if="ev.from_state" class="arrow">→</span>
              <span
                class="state-pill to"
                :class="{
                  alert: ev.to_state === 'on' || ev.to_state === 'open' || ev.to_state === 'detected',
                  safe: ev.to_state === 'off' || ev.to_state === 'closed' || ev.to_state === 'clear',
                }"
              >
                {{ ev.to_state }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.event-feed-drawer {
  position: absolute;
  width: 320px;
  background: var(--bg-surface-glass);
  backdrop-filter: blur(12px);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
  z-index: 150;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: max-height 0.25s ease-in-out, top 0.2s ease, bottom 0.2s ease, left 0.2s ease, right 0.2s ease;
  max-height: 42px;
}

/* Corner Docking */
.event-feed-drawer.dock-bottom-left {
  bottom: 16px;
  left: 16px;
}

.event-feed-drawer.dock-bottom-right {
  bottom: 16px;
  right: 16px;
}

.event-feed-drawer.dock-top-left {
  top: 72px;
  left: 16px;
}

.event-feed-drawer.dock-top-right {
  top: 72px;
  right: 16px;
}

.event-feed-drawer.open {
  max-height: 400px;
}

.drawer-header {
  height: 42px;
  padding: 0 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
  background: var(--bg-surface);
  user-select: none;
}

.drawer-header:hover {
  background: var(--bg-surface-hover);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.drawer-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.event-count {
  font-size: 10px;
  font-weight: 700;
  padding: 1px 6px;
  background: rgba(99, 102, 241, 0.25);
  color: #a5b4fc;
  border-radius: var(--radius-full);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.dock-btn {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: var(--radius-sm, 4px);
  padding: 3px 6px;
  color: var(--text-secondary);
  font-size: 11px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s ease;
}

.dock-btn:hover {
  background: rgba(99, 102, 241, 0.25);
  border-color: #6366f1;
  color: #ffffff;
}

.toggle-btn {
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
}

.drawer-content {
  display: flex;
  flex-direction: column;
  height: 350px;
}

.drawer-search {
  padding: 8px 10px;
  display: flex;
  gap: 6px;
  border-bottom: 1px solid var(--border-color);
}

.drawer-search input {
  flex: 1;
  font-size: 12px;
  padding: 4px 8px;
  height: 28px;
  border-radius: var(--radius-sm);
}

.clear-feed-btn {
  font-size: 11px;
  padding: 4px 8px;
  background: var(--bg-surface);
  color: var(--text-muted);
  border-radius: var(--radius-sm);
}

.clear-feed-btn:hover {
  color: var(--color-danger);
}

.events-scrollable {
  flex: 1;
  overflow-y: auto;
  padding: 6px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.empty-feed {
  padding: 24px;
  text-align: center;
  color: var(--text-muted);
  font-size: 12px;
}

.event-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all 0.15s ease;
}

.event-item:hover {
  background: rgba(99, 102, 241, 0.1);
  border-color: rgba(99, 102, 241, 0.3);
  transform: translateX(-2px);
}

.event-time {
  font-family: var(--font-mono, monospace);
  font-size: 10px;
  color: var(--text-muted);
}

.event-body {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  overflow: hidden;
}

.event-name {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 140px;
}

.event-state {
  display: flex;
  align-items: center;
  gap: 4px;
}

.state-pill {
  font-size: 10px;
  font-weight: 600;
  padding: 1px 5px;
  border-radius: var(--radius-xs);
  text-transform: capitalize;
}

.state-pill.from {
  color: var(--text-muted);
  background: rgba(255, 255, 255, 0.05);
}

.arrow {
  font-size: 10px;
  color: var(--text-muted);
}

.state-pill.to {
  color: var(--text-primary);
  background: rgba(255, 255, 255, 0.1);
}

.state-pill.to.alert {
  background: rgba(239, 68, 68, 0.2);
  color: #f87171;
  border: 1px solid rgba(239, 68, 68, 0.4);
}

.state-pill.to.safe {
  background: rgba(16, 185, 129, 0.2);
  color: #34d399;
  border: 1px solid rgba(16, 185, 129, 0.4);
}
</style>
