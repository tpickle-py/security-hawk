<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import type { Endpoint, Shape, SubArea } from "@/types/plan";

export interface ContextMenuState {
  show: boolean;
  x: number;
  y: number;
  type: "endpoint" | "room" | "subarea" | "wall" | "label" | "canvas";
  target?: Endpoint | Shape | SubArea | null;
}

const props = defineProps<{
  menuState: ContextMenuState;
}>();

const emit = defineEmits<{
  (e: "close"): void;
  (e: "action", actionName: string, payload?: any): void;
}>();

const menuRef = ref<HTMLDivElement | null>(null);

// Clamp position so menu doesn't go offscreen
const clampedPosition = computed(() => {
  const menuWidth = 240;
  const menuHeight = 320;
  const margin = 12;

  let x = props.menuState.x;
  let y = props.menuState.y;

  if (typeof window !== "undefined") {
    if (x + menuWidth > window.innerWidth - margin) {
      x = Math.max(margin, window.innerWidth - menuWidth - margin);
    }
    if (y + menuHeight > window.innerHeight - margin) {
      y = Math.max(margin, window.innerHeight - menuHeight - margin);
    }
  }

  return { x, y };
});

function handleItemClick(action: string, payload?: any) {
  emit("action", action, payload);
  emit("close");
}

function handleDocClick(e: MouseEvent) {
  if (menuRef.value && !menuRef.value.contains(e.target as Node)) {
    emit("close");
  }
}

function handleKeyDown(e: KeyboardEvent) {
  if (e.key === "Escape") {
    emit("close");
  }
}

onMounted(() => {
  window.addEventListener("mousedown", handleDocClick);
  window.addEventListener("keydown", handleKeyDown);
});

onUnmounted(() => {
  window.removeEventListener("mousedown", handleDocClick);
  window.removeEventListener("keydown", handleKeyDown);
});
</script>

<template>
  <Teleport to="body">
    <div
      v-if="menuState.show"
      ref="menuRef"
      class="context-menu glass-panel"
      :style="{ left: `${clampedPosition.x}px`, top: `${clampedPosition.y}px` }"
      @click.stop
      @contextmenu.prevent
    >
      <!-- Header Badge -->
      <div class="menu-header">
        <template v-if="menuState.type === 'endpoint'">
          <span class="header-icon">📍</span>
          <div class="header-info">
            <div class="header-title">{{ (menuState.target as Endpoint)?.label || (menuState.target as Endpoint)?.entity_id }}</div>
            <div class="header-meta">{{ (menuState.target as Endpoint)?.type?.toUpperCase() }}</div>
          </div>
        </template>

        <template v-else-if="menuState.type === 'room'">
          <span class="header-icon">🏠</span>
          <div class="header-info">
            <div class="header-title">{{ ((menuState.target as Shape)?.geometry as any)?.name || 'Room Polygon' }}</div>
            <div class="header-meta">Architectural Room</div>
          </div>
        </template>

        <template v-else-if="menuState.type === 'subarea'">
          <span class="header-icon">📐</span>
          <div class="header-info">
            <div class="header-title">{{ (menuState.target as SubArea)?.name }}</div>
            <div class="header-meta">Sub-Area / Zone</div>
          </div>
        </template>

        <template v-else-if="menuState.type === 'wall'">
          <span class="header-icon">🧱</span>
          <div class="header-info">
            <div class="header-title">Wall Segment</div>
            <div class="header-meta">{{ ((menuState.target as Shape)?.geometry as any)?.thickness || 8 }}px thickness</div>
          </div>
        </template>

        <template v-else-if="menuState.type === 'label'">
          <span class="header-icon">🏷️</span>
          <div class="header-info">
            <div class="header-title">Text Label</div>
            <div class="header-meta">{{ ((menuState.target as Shape)?.geometry as any)?.text }}</div>
          </div>
        </template>

        <template v-else>
          <span class="header-icon">📐</span>
          <div class="header-info">
            <div class="header-title">Editor Canvas</div>
            <div class="header-meta">Floor Plan Actions</div>
          </div>
        </template>
      </div>

      <div class="menu-divider"></div>

      <!-- Action Items: Endpoint -->
      <div v-if="menuState.type === 'endpoint'" class="menu-items">
        <button class="menu-item" @click="handleItemClick('open-properties')">
          <span class="item-icon">⚙️</span>
          <span>Properties & Configuration</span>
        </button>
        <button class="menu-item" @click="handleItemClick('rotate-cw')">
          <span class="item-icon">🔄</span>
          <span>Rotate 90° Clockwise</span>
        </button>
        <button class="menu-item" @click="handleItemClick('rotate-ccw')">
          <span class="item-icon">↺</span>
          <span>Rotate 90° Counter-CW</span>
        </button>
        <button class="menu-item" @click="handleItemClick('invert-180')">
          <span class="item-icon">↕️</span>
          <span>Invert 180°</span>
        </button>
        <button class="menu-item" @click="handleItemClick('duplicate')">
          <span class="item-icon">📋</span>
          <span>Duplicate Entity</span>
        </button>
        <div class="menu-divider"></div>
        <button class="menu-item danger" @click="handleItemClick('delete')">
          <span class="item-icon">🗑️</span>
          <span>Delete Endpoint</span>
        </button>
      </div>

      <!-- Action Items: Room / SubArea -->
      <div v-else-if="menuState.type === 'room' || menuState.type === 'subarea'" class="menu-items">
        <button class="menu-item" @click="handleItemClick('rename-room')">
          <span class="item-icon">✏️</span>
          <span>Rename Room</span>
        </button>
        <button class="menu-item" @click="handleItemClick('change-color')">
          <span class="item-icon">🎨</span>
          <span>Change Style / Color</span>
        </button>
        <button class="menu-item" @click="handleItemClick('duplicate')">
          <span class="item-icon">📋</span>
          <span>Duplicate Room</span>
        </button>
        <button class="menu-item" @click="handleItemClick('open-properties')">
          <span class="item-icon">⚙️</span>
          <span>View Properties</span>
        </button>
        <div class="menu-divider"></div>
        <button class="menu-item danger" @click="handleItemClick('delete')">
          <span class="item-icon">🗑️</span>
          <span>Delete Room</span>
        </button>
      </div>

      <!-- Action Items: Wall -->
      <div v-else-if="menuState.type === 'wall'" class="menu-items">
        <button class="menu-item" @click="handleItemClick('add-door')">
          <span class="item-icon">🚪</span>
          <span>Add Door Cutout</span>
        </button>
        <button class="menu-item" @click="handleItemClick('add-window')">
          <span class="item-icon">🪟</span>
          <span>Add Window Cutout</span>
        </button>
        <button class="menu-item" @click="handleItemClick('open-properties')">
          <span class="item-icon">⚙️</span>
          <span>Wall Properties</span>
        </button>
        <div class="menu-divider"></div>
        <button class="menu-item danger" @click="handleItemClick('delete')">
          <span class="item-icon">🗑️</span>
          <span>Delete Wall</span>
        </button>
      </div>

      <!-- Action Items: Label -->
      <div v-else-if="menuState.type === 'label'" class="menu-items">
        <button class="menu-item" @click="handleItemClick('edit-label')">
          <span class="item-icon">✏️</span>
          <span>Edit Label Text</span>
        </button>
        <div class="menu-divider"></div>
        <button class="menu-item danger" @click="handleItemClick('delete')">
          <span class="item-icon">🗑️</span>
          <span>Delete Label</span>
        </button>
      </div>

      <!-- Action Items: Canvas Background -->
      <div v-else class="menu-items">
        <button class="menu-item highlight" @click="handleItemClick('insert-room-grid')">
          <span class="item-icon">▦</span>
          <span>Insert Rooms Grid (Table)...</span>
        </button>
        <button class="menu-item" @click="handleItemClick('tool-wall')">
          <span class="item-icon">🧱</span>
          <span>Draw Architectural Wall (W)</span>
        </button>
        <button class="menu-item" @click="handleItemClick('tool-room')">
          <span class="item-icon">🏠</span>
          <span>Draw Room Polygon (REC)</span>
        </button>
        <button class="menu-item" @click="handleItemClick('tool-label')">
          <span class="item-icon">🏷️</span>
          <span>Insert Text Label</span>
        </button>
        <div class="menu-divider"></div>
        <button class="menu-item" @click="handleItemClick('toggle-cad')">
          <span class="item-icon">⌨️</span>
          <span>AutoCAD Command Bar</span>
        </button>
        <button class="menu-item" @click="handleItemClick('calibrate-scale')">
          <span class="item-icon">📐</span>
          <span>Calibrate Scale</span>
        </button>
        <button class="menu-item" @click="handleItemClick('zoom-fit')">
          <span class="item-icon">🔍</span>
          <span>Zoom to Fit (100%)</span>
        </button>
        <div class="menu-divider"></div>
        <button class="menu-item" @click="handleItemClick('save-plan')">
          <span class="item-icon">💾</span>
          <span>Save Plan (Ctrl+S)</span>
        </button>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.context-menu {
  position: fixed;
  z-index: 10000;
  width: 240px;
  background: rgba(15, 23, 42, 0.95);
  backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: var(--radius-md, 10px);
  box-shadow: 0 12px 36px rgba(0, 0, 0, 0.6), 0 0 0 1px rgba(99, 102, 241, 0.2);
  padding: 6px;
  user-select: none;
  animation: contextMenuFadeIn 0.12s ease-out;
}

@keyframes contextMenuFadeIn {
  from {
    opacity: 0;
    transform: scale(0.96) translateY(-4px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

.menu-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
}

.header-icon {
  font-size: 16px;
}

.header-info {
  flex: 1;
  overflow: hidden;
}

.header-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary, #ffffff);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.header-meta {
  font-size: 10px;
  color: var(--text-muted, #94a3b8);
  font-family: var(--font-mono, monospace);
  margin-top: 1px;
}

.menu-divider {
  height: 1px;
  background: rgba(255, 255, 255, 0.08);
  margin: 4px 6px;
}

.menu-items {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 7px 10px;
  background: transparent;
  border: none;
  border-radius: var(--radius-sm, 6px);
  color: var(--text-secondary, #cbd5e1);
  font-size: 12px;
  font-weight: 500;
  text-align: left;
  cursor: pointer;
  transition: all 0.12s ease;
  width: 100%;
}

.menu-item:hover {
  background: rgba(99, 102, 241, 0.16);
  color: #ffffff;
}

.menu-item.highlight {
  color: #818cf8;
}

.menu-item.highlight:hover {
  background: rgba(99, 102, 241, 0.25);
  color: #ffffff;
}

.menu-item.danger {
  color: #f87171;
}

.menu-item.danger:hover {
  background: rgba(239, 68, 68, 0.18);
  color: #ffffff;
}

.item-icon {
  font-size: 13px;
  width: 16px;
  display: flex;
  justify-content: center;
}
</style>
