<script setup lang="ts">
import { ref, computed, nextTick, onMounted, onUnmounted } from "vue";
import { useEditorStore } from "@/stores/editorStore";
import { usePlanStore } from "@/stores/planStore";

interface QuickChip {
  label: string;
  command: string;
  icon?: string;
}

const emit = defineEmits<{
  (e: "open-grid-modal"): void;
  (e: "open-export-modal"): void;
  (e: "open-history-modal"): void;
}>();

const editorStore = useEditorStore();
const planStore = usePlanStore();

// Command definitions
export interface CadCommandDef {
  command: string;
  aliases: string[];
  description: string;
  category: "Draw" | "Modify" | "View" | "File";
  action: (args: string[]) => string | void;
}

const isMinimized = ref(false);
const showHelper = ref(false);
const inputCommand = ref("");
const commandHistory = ref<Array<{ type: "input" | "output" | "error"; text: string }>>([
  { type: "output", text: "Security Hawk Command Line initialized. Type HELP or ? for commands." },
]);
const historyIndex = ref(-1);
const pastInputs = ref<string[]>([]);
const logContainerRef = ref<HTMLDivElement | null>(null);
const inputRef = ref<HTMLInputElement | null>(null);

// Docking state: 'bottom' | 'top' | 'float'
export type CadDock = "bottom" | "top" | "float";
const dockMode = ref<CadDock>(getInitialDock());

// Floating coordinates
const floatX = ref(60);
const floatY = ref(600);
const isDraggingFloat = ref(false);

function getInitialDock(): CadDock {
  try {
    const saved = localStorage.getItem("sh_cad_dock");
    if (saved && ["bottom", "top", "float"].includes(saved)) {
      return saved as CadDock;
    }
  } catch {}
  return "bottom";
}

function setDockMode(mode: CadDock) {
  dockMode.value = mode;
  try {
    localStorage.setItem("sh_cad_dock", mode);
  } catch {}
}

function cycleDockMode() {
  const modes: CadDock[] = ["bottom", "top", "float"];
  const next = modes[(modes.indexOf(dockMode.value) + 1) % modes.length];
  setDockMode(next);
}

// Commands list
const commandsList: CadCommandDef[] = [
  // Draw
  {
    command: "WALL",
    aliases: ["W", "LINE", "L"],
    description: "Draw architectural walls between points",
    category: "Draw",
    action: () => {
      editorStore.setTool("wall");
      return "Wall tool activated. Click canvas points to draw wall segments.";
    },
  },
  {
    command: "ROOM",
    aliases: ["REC", "POLY", "R"],
    description: "Draw architectural room polygon (double-click to close)",
    category: "Draw",
    action: () => {
      editorStore.setTool("room");
      return "Room polygon tool activated. Click 3+ points then double-click to close.";
    },
  },
  {
    command: "DOOR",
    aliases: ["D"],
    description: "Insert door cutout with swing arc onto wall",
    category: "Draw",
    action: () => {
      editorStore.setTool("door");
      return "Door tool activated. Click on any wall to place a door cutout.";
    },
  },
  {
    command: "WINDOW",
    aliases: ["WIN"],
    description: "Insert window opening cutout onto wall",
    category: "Draw",
    action: () => {
      editorStore.setTool("window");
      return "Window tool activated. Click on any wall to place a window cutout.";
    },
  },
  {
    command: "GRID",
    aliases: ["TABLE", "RMGRID"],
    description: "Insert Room Grid overlay (Word-table style matrix)",
    category: "Draw",
    action: () => {
      emit("open-grid-modal");
      return "Opened Room & Subsections Grid Overlay dialog.";
    },
  },
  {
    command: "LABEL",
    aliases: ["TEXT", "T", "LBL"],
    description: "Insert text label onto floor plan",
    category: "Draw",
    action: () => {
      editorStore.setTool("label");
      return "Label tool activated. Click canvas to position text label.";
    },
  },
  {
    command: "SCALE",
    aliases: ["CAL"],
    description: "Calibrate floor plan scale distance between 2 points",
    category: "Draw",
    action: () => {
      editorStore.startScaleCalibration();
      return "Scale tool active. Click two points on floor plan to calibrate real meters.";
    },
  },

  // Modify
  {
    command: "SELECT",
    aliases: ["SEL"],
    description: "Activate selection tool for endpoints, rooms, and walls",
    category: "Modify",
    action: () => {
      editorStore.setTool("select");
      return "Select tool activated. Click or box-select items on canvas.";
    },
  },
  {
    command: "ROTATE",
    aliases: ["RO"],
    description: "Rotate selected endpoints by angle (e.g. RO 90 or RO -90)",
    category: "Modify",
    action: (args) => {
      const angle = parseInt(args[0] || "90", 10);
      if (editorStore.selectedEndpointIds.length === 0) {
        return "No endpoints selected to rotate.";
      }
      for (const id of editorStore.selectedEndpointIds) {
        const ep = planStore.currentEndpoints.find((e) => e.id === id);
        if (ep) {
          const next = ((ep.rotation || 0) + angle + 360) % 360;
          planStore.updateEndpoint(id, { rotation: next });
        }
      }
      return `Rotated ${editorStore.selectedEndpointIds.length} endpoint(s) by ${angle}°.`;
    },
  },
  {
    command: "GROUP",
    aliases: ["GRP"],
    description: "Group selected endpoints into a logical unit (e.g. GROUP Rack Unit)",
    category: "Modify",
    action: (args) => {
      if (editorStore.selectedEndpointIds.length < 2) {
        return "Select 2 or more endpoints to group.";
      }
      const name = args.join(" ").trim() || "Grouped Unit";
      planStore.groupEndpoints(editorStore.selectedEndpointIds, name);
      return `Grouped ${editorStore.selectedEndpointIds.length} item(s) as "${name}".`;
    },
  },
  {
    command: "UNGROUP",
    aliases: ["UNGRP"],
    description: "Ungroup currently selected endpoints",
    category: "Modify",
    action: () => {
      if (editorStore.selectedEndpointIds.length === 0) {
        return "No endpoints selected to ungroup.";
      }
      planStore.ungroupEndpoints(editorStore.selectedEndpointIds);
      return `Ungrouped ${editorStore.selectedEndpointIds.length} item(s).`;
    },
  },
  {
    command: "DELETE",
    aliases: ["DEL", "ERASE"],
    description: "Delete currently selected endpoints, shapes, or rooms",
    category: "Modify",
    action: () => {
      let count = 0;
      if (editorStore.selectedEndpointIds.length > 0) {
        count += editorStore.selectedEndpointIds.length;
        for (const id of [...editorStore.selectedEndpointIds]) {
          planStore.removeEndpoint(id);
        }
        editorStore.clearSelection();
      }
      if (editorStore.selectedShapeId) {
        planStore.removeShape(editorStore.selectedShapeId);
        editorStore.selectedShapeId = null;
        count++;
      }
      if (editorStore.selectedSubAreaId) {
        planStore.removeSubArea(editorStore.selectedSubAreaId);
        editorStore.selectedSubAreaId = null;
        count++;
      }
      return count > 0 ? `Deleted ${count} item(s).` : "Nothing selected to delete.";
    },
  },
  {
    command: "DESELECT",
    aliases: ["CLEAR", "ESC"],
    description: "Clear active selection or cancel current tool",
    category: "Modify",
    action: () => {
      editorStore.clearSelection();
      editorStore.setTool("select");
      return "Selection cleared.";
    },
  },
  {
    command: "UNDO",
    aliases: ["U"],
    description: "Undo last modification",
    category: "Modify",
    action: () => {
      planStore.performUndo();
      return "Undone.";
    },
  },
  {
    command: "REDO",
    aliases: [],
    description: "Redo previously undone modification",
    category: "Modify",
    action: () => {
      planStore.performRedo();
      return "Redone.";
    },
  },

  // View
  {
    command: "PAN",
    aliases: ["P"],
    description: "Activate canvas pan tool",
    category: "View",
    action: () => {
      editorStore.setTool("pan");
      return "Pan tool activated. Drag canvas to pan.";
    },
  },
  {
    command: "ZOOM",
    aliases: ["Z"],
    description: "Zoom canvas (options: IN, OUT, FIT, 100)",
    category: "View",
    action: (args) => {
      const sub = (args[0] || "IN").toUpperCase();
      if (sub === "IN") {
        editorStore.zoomIn();
        return `Zoomed in (${Math.round(editorStore.zoom * 100)}%).`;
      } else if (sub === "OUT") {
        editorStore.zoomOut();
        return `Zoomed out (${Math.round(editorStore.zoom * 100)}%).`;
      } else if (sub === "FIT" || sub === "ALL" || sub === "EXTENTS") {
        editorStore.resetView();
        return "Zoom reset to 100%.";
      }
      editorStore.zoomIn();
      return `Zoom: ${Math.round(editorStore.zoom * 100)}%`;
    },
  },

  // File
  {
    command: "QSAVE",
    aliases: ["SAVE"],
    description: "Save current plan to Home Assistant backend",
    category: "File",
    action: () => {
      planStore.savePlan();
      return "Saving floor plan...";
    },
  },
  {
    command: "EXPORT",
    aliases: ["EXP"],
    description: "Open Export Plan dialog (SVG, PNG, or JSON)",
    category: "File",
    action: () => {
      emit("open-export-modal");
      return "Export dialog opened.";
    },
  },
  {
    command: "HISTORY",
    aliases: ["HIST"],
    description: "Open Version History restore dialog",
    category: "File",
    action: () => {
      emit("open-history-modal");
      return "Version History dialog opened.";
    },
  },
  {
    command: "HELP",
    aliases: ["?"],
    description: "Display or toggle command helper guide",
    category: "File",
    action: () => {
      showHelper.value = !showHelper.value;
      return showHelper.value ? "Opened command helper." : "Closed command helper.";
    },
  },
  {
    command: "CLS",
    aliases: ["CLEARLOG"],
    description: "Clear command line log output",
    category: "File",
    action: () => {
      commandHistory.value = [];
      return "Log cleared.";
    },
  },
  {
    command: "AUDIT",
    aliases: ["SECURITY", "COVERAGE"],
    description: "Run AI security coverage & gap audit",
    category: "View",
    action: () => {
      editorStore.showCoverageAuditModal = true;
      return "Security Coverage Audit opened.";
    },
  },
  {
    command: "ZEN",
    aliases: ["FULLSCREEN", "CLEAN"],
    description: "Activate Zen Mode (all panels minimized for full canvas focus)",
    category: "View",
    action: () => {
      editorStore.setWorkspacePreset("zen");
      return "Zen mode activated.";
    },
  },
];

// Contextual quick chips
const contextualChips = computed<QuickChip[]>(() => {
  if (editorStore.selectedEndpointId || editorStore.selectedEndpointIds.length > 0) {
    const chips: QuickChip[] = [
      { label: "Rotate 90°", command: "ROTATE 90", icon: "↻" },
      { label: "Rotate -90°", command: "ROTATE -90", icon: "↺" },
    ];
    if (editorStore.selectedEndpointIds.length > 1) {
      chips.push({ label: "Group", command: "GROUP", icon: "🔗" });
    }
    const hasGrouped = editorStore.selectedEndpointIds.some((id) => {
      const ep = planStore.currentEndpoints.find((e) => e.id === id);
      return ep && ep.group_id;
    });
    if (hasGrouped) {
      chips.push({ label: "Ungroup", command: "UNGROUP", icon: "🔓" });
    }
    chips.push(
      { label: "Delete", command: "DELETE", icon: "🗑️" },
      { label: "Deselect", command: "DESELECT", icon: "✕" },
    );
    return chips;
  }
  if (editorStore.selectedSubAreaId || editorStore.selectedShapeId) {
    return [
      { label: "Rename", command: "RENAME", icon: "✏️" },
      { label: "Room Grid", command: "GRID", icon: "⊞" },
      { label: "Delete", command: "DELETE", icon: "🗑️" },
      { label: "Deselect", command: "DESELECT", icon: "✕" },
    ];
  }
  return [
    { label: "Wall", command: "WALL", icon: "🧱" },
    { label: "Room", command: "ROOM", icon: "⬛" },
    { label: "Door", command: "DOOR", icon: "🚪" },
    { label: "Window", command: "WINDOW", icon: "🪟" },
    { label: "Audit", command: "AUDIT", icon: "🛡️" },
    { label: "Grid Matrix", command: "GRID", icon: "⊞" },
    { label: "Calibrate", command: "SCALE", icon: "📏" },
    { label: "Zoom Fit", command: "ZOOM EXTENTS", icon: "🔍" },
  ];
});

function executeChip(cmdStr: string) {
  inputCommand.value = cmdStr;
  executeCommand();
}

// Autocomplete suggestions
const suggestions = computed(() => {
  const query = inputCommand.value.trim().toUpperCase();
  if (!query) return [];
  return commandsList.filter(
    (cmd) =>
      cmd.command.startsWith(query) ||
      cmd.aliases.some((a) => a.startsWith(query))
  );
});

function applySuggestion(cmd: CadCommandDef) {
  inputCommand.value = cmd.command;
  executeCommand();
}

function executeCommand() {
  const raw = inputCommand.value.trim();
  if (!raw) return;

  pastInputs.value.push(raw);
  historyIndex.value = -1;

  commandHistory.value.push({ type: "input", text: `Command: ${raw}` });

  const parts = raw.split(/\s+/);
  const trigger = parts[0].toUpperCase();
  const args = parts.slice(1);

  const matched = commandsList.find(
    (c) => c.command === trigger || c.aliases.includes(trigger)
  );

  if (matched) {
    try {
      const res = matched.action(args);
      if (res) {
        commandHistory.value.push({ type: "output", text: res });
      }
    } catch (err: any) {
      commandHistory.value.push({ type: "error", text: `Error: ${err?.message || err}` });
    }
  } else {
    commandHistory.value.push({
      type: "error",
      text: `Unknown command "${trigger}". Type HELP or ? to list commands.`,
    });
  }

  inputCommand.value = "";

  nextTick(() => {
    if (logContainerRef.value) {
      logContainerRef.value.scrollTop = logContainerRef.value.scrollHeight;
    }
  });
}

function handleKeyDown(e: KeyboardEvent) {
  if (e.key === "Enter") {
    executeCommand();
  } else if (e.key === "ArrowUp") {
    e.preventDefault();
    if (pastInputs.value.length === 0) return;
    if (historyIndex.value === -1) {
      historyIndex.value = pastInputs.value.length - 1;
    } else if (historyIndex.value > 0) {
      historyIndex.value--;
    }
    inputCommand.value = pastInputs.value[historyIndex.value] || "";
  } else if (e.key === "ArrowDown") {
    e.preventDefault();
    if (historyIndex.value !== -1) {
      if (historyIndex.value < pastInputs.value.length - 1) {
        historyIndex.value++;
        inputCommand.value = pastInputs.value[historyIndex.value] || "";
      } else {
        historyIndex.value = -1;
        inputCommand.value = "";
      }
    }
  } else if (e.key === "Escape") {
    inputCommand.value = "";
    editorStore.clearSelection();
  }
}

// Drag header for floating dock
function startHeaderDrag(e: MouseEvent) {
  if (dockMode.value !== "float") return;
  isDraggingFloat.value = true;
  const startX = e.clientX;
  const startY = e.clientY;
  const origX = floatX.value;
  const origY = floatY.value;

  const onMouseMove = (ev: MouseEvent) => {
    floatX.value = Math.max(10, Math.min(window.innerWidth - 300, origX + (ev.clientX - startX)));
    floatY.value = Math.max(10, Math.min(window.innerHeight - 80, origY + (ev.clientY - startY)));
  };

  const onMouseUp = () => {
    isDraggingFloat.value = false;
    window.removeEventListener("mousemove", onMouseMove);
    window.removeEventListener("mouseup", onMouseUp);
  };

  window.addEventListener("mousemove", onMouseMove);
  window.addEventListener("mouseup", onMouseUp);
}

function focusInput() {
  inputRef.value?.focus();
}

function handleGlobalKeydown(e: KeyboardEvent) {
  const target = e.target as HTMLElement;
  if (
    target &&
    (target.tagName === "INPUT" ||
      target.tagName === "TEXTAREA" ||
      target.tagName === "SELECT" ||
      target.isContentEditable)
  ) {
    return;
  }
  if (e.key === "/" || e.key === ":") {
    e.preventDefault();
    editorStore.showCadCommandBar = true;
    isMinimized.value = false;
    nextTick(() => {
      inputRef.value?.focus();
    });
  }
}

function onWorkspacePreset(e: Event) {
  const detail = (e as CustomEvent).detail;
  if (!detail) return;
  if (detail.preset === "cad") {
    editorStore.showCadCommandBar = true;
    isMinimized.value = false;
    setDockMode("bottom");
  } else if (detail.preset === "zen") {
    editorStore.showCadCommandBar = false;
  }
}

onMounted(() => {
  window.addEventListener("keydown", handleGlobalKeydown);
  window.addEventListener("sh-workspace-preset", onWorkspacePreset);
  focusInput();
});

onUnmounted(() => {
  window.removeEventListener("keydown", handleGlobalKeydown);
  window.removeEventListener("sh-workspace-preset", onWorkspacePreset);
});
</script>

<template>
  <div
    :class="[
      'cad-command-bar',
      'glass-panel',
      `dock-${dockMode}`,
      { minimized: isMinimized },
    ]"
    :style="dockMode === 'float' ? { left: `${floatX}px`, top: `${floatY}px` } : undefined"
  >
    <!-- Bar Header / Status Strip -->
    <div class="cad-header" @mousedown="startHeaderDrag">
      <div class="cad-title-group">
        <span class="cad-logo">⌨️</span>
        <span class="cad-title">Command Bar</span>
        <span class="cad-active-tool">Tool: [{{ editorStore.activeTool.toUpperCase() }}]</span>
      </div>

      <div class="cad-header-actions" @mousedown.stop>
        <button
          class="cad-btn"
          :class="{ active: showHelper }"
          title="Toggle Command Helper Guide"
          @click="showHelper = !showHelper"
        >
          ❓ Helper
        </button>
        <button
          class="cad-btn"
          :title="`Dock: ${dockMode.toUpperCase()}. Click to cycle (Bottom, Top, Float)`"
          @click="cycleDockMode"
        >
          ⚓ {{ dockMode.toUpperCase() }}
        </button>
        <button
          class="cad-btn"
          :title="isMinimized ? 'Expand Command Line' : 'Minimize Command Line'"
          @click="isMinimized = !isMinimized"
        >
          {{ isMinimized ? '▲' : '─' }}
        </button>
      </div>
    </div>

    <!-- Collapsed View Body -->
    <template v-if="!isMinimized">
      <!-- Terminal Output Log -->
      <div ref="logContainerRef" class="cad-log-container">
        <div
          v-for="(entry, idx) in commandHistory"
          :key="idx"
          :class="['cad-log-line', entry.type]"
        >
          {{ entry.text }}
        </div>
      </div>

      <!-- Autocomplete Dropdown -->
      <div v-if="suggestions.length > 0 && inputCommand.trim()" class="cad-autocomplete">
        <button
          v-for="s in suggestions.slice(0, 5)"
          :key="s.command"
          class="suggestion-item"
          @mousedown.prevent="applySuggestion(s)"
        >
          <span class="sugg-cmd">{{ s.command }}</span>
          <span v-if="s.aliases.length" class="sugg-alias">({{ s.aliases.join(', ') }})</span>
          <span class="sugg-desc">{{ s.description }}</span>
        </button>
      </div>

      <!-- Contextual Quick Action Chips -->
      <div class="cad-quick-chips">
        <span class="chips-label">Quick:</span>
        <button
          v-for="chip in contextualChips"
          :key="chip.label"
          class="cad-chip-btn"
          @click="executeChip(chip.command)"
        >
          <span v-if="chip.icon" class="chip-icon">{{ chip.icon }}</span>
          <span>{{ chip.label }}</span>
        </button>
      </div>

      <!-- Prompt Input Line -->
      <div class="cad-prompt-row">
        <span class="cad-prompt-prefix">Command:</span>
        <input
          ref="inputRef"
          type="text"
          v-model="inputCommand"
          class="cad-input"
          placeholder="Type a command (e.g. WALL, ROOM, DOOR, ZOOM, SAVE) or ? for help"
          autofocus
          @keydown="handleKeyDown"
        />
        <button class="cad-exec-btn" @click="executeCommand" title="Execute Command (Enter)">
          ↵ Run
        </button>
      </div>
    </template>

    <!-- Floating Helper Cheat Sheet Modal / Drawer -->
    <div v-if="showHelper" class="cad-helper-drawer glass-panel" @mousedown.stop>
      <div class="helper-header">
        <div class="helper-title">
          <span>📐 Command Reference</span>
        </div>
        <button class="helper-close-btn" @click="showHelper = false" title="Close Helper (Esc)">×</button>
      </div>

      <div class="helper-body">
        <div class="helper-section">
          <div class="section-title">Draw Commands</div>
          <div class="helper-table">
            <div class="helper-row" @click="applySuggestion(commandsList[0])">
              <span class="cmd-chip">WALL / W</span>
              <span class="cmd-desc">Draw connected wall vectors</span>
            </div>
            <div class="helper-row" @click="applySuggestion(commandsList[1])">
              <span class="cmd-chip">ROOM / REC</span>
              <span class="cmd-desc">Draw room polygon boundary</span>
            </div>
            <div class="helper-row" @click="applySuggestion(commandsList[2])">
              <span class="cmd-chip">DOOR / D</span>
              <span class="cmd-desc">Insert door cutout on wall</span>
            </div>
            <div class="helper-row" @click="applySuggestion(commandsList[3])">
              <span class="cmd-chip">WINDOW / WIN</span>
              <span class="cmd-desc">Insert window cutout on wall</span>
            </div>
            <div class="helper-row" @click="applySuggestion(commandsList[4])">
              <span class="cmd-chip">GRID / TABLE</span>
              <span class="cmd-desc">Insert Room Grid Matrix overlay</span>
            </div>
            <div class="helper-row" @click="applySuggestion(commandsList[5])">
              <span class="cmd-chip">LABEL / T</span>
              <span class="cmd-desc">Place architectural text label</span>
            </div>
            <div class="helper-row" @click="applySuggestion(commandsList[6])">
              <span class="cmd-chip">SCALE / CAL</span>
              <span class="cmd-desc">Calibrate real meters scale</span>
            </div>
          </div>
        </div>

        <div class="helper-section">
          <div class="section-title">Modify & Navigation</div>
          <div class="helper-table">
            <div class="helper-row" @click="applySuggestion(commandsList[7])">
              <span class="cmd-chip">SELECT / SEL</span>
              <span class="cmd-desc">Selection tool / Marquee</span>
            </div>
            <div class="helper-row" @click="applySuggestion(commandsList[8])">
              <span class="cmd-chip">ROTATE / RO</span>
              <span class="cmd-desc">Rotate selected endpoints (+/- deg)</span>
            </div>
            <div class="helper-row" @click="applySuggestion(commandsList[9])">
              <span class="cmd-chip">DELETE / DEL</span>
              <span class="cmd-desc">Delete selected elements</span>
            </div>
            <div class="helper-row" @click="applySuggestion(commandsList[10])">
              <span class="cmd-chip">CLEAR / ESC</span>
              <span class="cmd-desc">Clear active selection</span>
            </div>
            <div class="helper-row" @click="applySuggestion(commandsList[11])">
              <span class="cmd-chip">UNDO / U</span>
              <span class="cmd-desc">Undo last change</span>
            </div>
            <div class="helper-row" @click="applySuggestion(commandsList[13])">
              <span class="cmd-chip">PAN / P</span>
              <span class="cmd-desc">Pan canvas view</span>
            </div>
            <div class="helper-row" @click="applySuggestion(commandsList[14])">
              <span class="cmd-chip">ZOOM / Z</span>
              <span class="cmd-desc">Zoom IN / OUT / FIT</span>
            </div>
          </div>
        </div>

        <div class="helper-section">
          <div class="section-title">File & Utility</div>
          <div class="helper-table">
            <div class="helper-row" @click="applySuggestion(commandsList[15])">
              <span class="cmd-chip">SAVE / QSAVE</span>
              <span class="cmd-desc">Quick save floor plan</span>
            </div>
            <div class="helper-row" @click="applySuggestion(commandsList[16])">
              <span class="cmd-chip">EXPORT / EXP</span>
              <span class="cmd-desc">Export SVG / PNG / JSON</span>
            </div>
            <div class="helper-row" @click="applySuggestion(commandsList[17])">
              <span class="cmd-chip">HISTORY / HIST</span>
              <span class="cmd-desc">Version snapshots & rollback</span>
            </div>
            <div class="helper-row" @click="applySuggestion(commandsList[19])">
              <span class="cmd-chip">CLS</span>
              <span class="cmd-desc">Clear command line output</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.cad-command-bar {
  position: absolute;
  z-index: 180;
  display: flex;
  flex-direction: column;
  background: rgba(15, 23, 42, 0.94);
  backdrop-filter: blur(14px);
  border: 1px solid rgba(255, 255, 255, 0.12);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
  font-family: var(--font-mono, monospace);
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

/* Dock Bottom: Classic command bar */
.cad-command-bar.dock-bottom {
  bottom: 12px;
  left: 50%;
  transform: translateX(-50%);
  width: min(920px, calc(100% - 40px));
  border-radius: var(--radius-md, 10px);
}

/* Dock Top: Below top bar */
.cad-command-bar.dock-top {
  top: 70px;
  left: 50%;
  transform: translateX(-50%);
  width: min(920px, calc(100% - 40px));
  border-radius: var(--radius-md, 10px);
}

/* Dock Float: Free floating window */
.cad-command-bar.dock-float {
  width: 580px;
  border-radius: var(--radius-md, 10px);
}

.cad-command-bar.minimized {
  width: auto;
  min-width: 260px;
}

.cad-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 12px;
  background: rgba(0, 0, 0, 0.3);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  user-select: none;
  cursor: grab;
}

.cad-title-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.cad-logo {
  font-size: 13px;
}

.cad-title {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.5px;
  text-transform: uppercase;
  color: #94a3b8;
}

.cad-active-tool {
  font-size: 10px;
  color: #818cf8;
  font-weight: 600;
}

.cad-header-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.cad-btn {
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #cbd5e1;
  font-size: 10px;
  font-weight: 600;
  padding: 2px 7px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.cad-btn:hover {
  background: rgba(99, 102, 241, 0.2);
  border-color: #6366f1;
  color: #ffffff;
}

.cad-btn.active {
  background: #6366f1;
  color: #ffffff;
}

.cad-log-container {
  height: 64px;
  overflow-y: auto;
  padding: 6px 12px;
  display: flex;
  flex-direction: column;
  gap: 3px;
  font-size: 11px;
  line-height: 1.4;
  background: rgba(0, 0, 0, 0.2);
}

.cad-log-line.input {
  color: #94a3b8;
}

.cad-log-line.output {
  color: #38bdf8;
}

.cad-log-line.error {
  color: #f87171;
}

.cad-autocomplete {
  position: absolute;
  bottom: 42px;
  left: 12px;
  right: 12px;
  background: rgba(15, 23, 42, 0.98);
  border: 1px solid rgba(99, 102, 241, 0.4);
  border-radius: 6px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.6);
  overflow: hidden;
  z-index: 190;
  display: flex;
  flex-direction: column;
}

.suggestion-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  background: transparent;
  border: none;
  color: #cbd5e1;
  font-family: inherit;
  font-size: 11px;
  text-align: left;
  cursor: pointer;
  transition: background 0.12s ease;
}

.suggestion-item:hover {
  background: rgba(99, 102, 241, 0.25);
  color: #ffffff;
}

.sugg-cmd {
  font-weight: 700;
  color: #818cf8;
}

.sugg-alias {
  color: #64748b;
  font-size: 10px;
}

.sugg-desc {
  margin-left: auto;
  color: #94a3b8;
  font-size: 10px;
}

.cad-quick-chips {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 12px;
  background: rgba(0, 0, 0, 0.35);
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  overflow-x: auto;
  white-space: nowrap;
}

.chips-label {
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #64748b;
  margin-right: 2px;
}

.cad-chip-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 4px;
  padding: 2px 8px;
  font-size: 11px;
  font-family: inherit;
  font-weight: 500;
  color: #cbd5e1;
  cursor: pointer;
  transition: all 0.15s ease;
}

.cad-chip-btn:hover {
  background: rgba(99, 102, 241, 0.25);
  border-color: rgba(99, 102, 241, 0.5);
  color: #ffffff;
}

.chip-icon {
  font-size: 11px;
}

.cad-prompt-row {
  display: flex;
  align-items: center;
  padding: 6px 10px;
  gap: 8px;
  background: rgba(0, 0, 0, 0.4);
}

.cad-prompt-prefix {
  font-size: 12px;
  font-weight: 700;
  color: #e2e8f0;
}

.cad-input {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  font-family: inherit;
  font-size: 12px;
  color: #ffffff;
}

.cad-input::placeholder {
  color: #64748b;
  font-size: 11px;
}

.cad-exec-btn {
  background: rgba(99, 102, 241, 0.25);
  border: 1px solid rgba(99, 102, 241, 0.4);
  color: #ffffff;
  font-family: inherit;
  font-size: 11px;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.cad-exec-btn:hover {
  background: #6366f1;
}

/* Helper Drawer / Popover */
.cad-helper-drawer {
  position: absolute;
  bottom: calc(100% + 8px);
  right: 0;
  width: 440px;
  max-height: 420px;
  overflow-y: auto;
  background: rgba(15, 23, 42, 0.98);
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: var(--radius-md, 10px);
  box-shadow: 0 16px 40px rgba(0, 0, 0, 0.7);
  z-index: 200;
  display: flex;
  flex-direction: column;
}

.helper-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  background: rgba(0, 0, 0, 0.3);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.helper-title {
  font-size: 12px;
  font-weight: 700;
  color: #ffffff;
}

.helper-close-btn {
  background: transparent;
  border: none;
  color: #94a3b8;
  font-size: 18px;
  cursor: pointer;
  line-height: 1;
}

.helper-close-btn:hover {
  color: #ffffff;
}

.helper-body {
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.section-title {
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  color: #818cf8;
  letter-spacing: 0.5px;
  margin-bottom: 6px;
}

.helper-table {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.helper-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 5px 8px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.12s ease;
}

.helper-row:hover {
  background: rgba(99, 102, 241, 0.2);
}

.cmd-chip {
  font-size: 11px;
  font-weight: 700;
  color: #e2e8f0;
}

.cmd-desc {
  font-size: 11px;
  color: #94a3b8;
}
</style>
