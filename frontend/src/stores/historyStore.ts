import { defineStore } from "pinia";
import { ref, computed } from "vue";
import type { Site } from "@/types/plan";

const MAX_HISTORY = 40;

export const useHistoryStore = defineStore("history", () => {
  const undoStack = ref<string[]>([]);
  const redoStack = ref<string[]>([]);

  const canUndo = computed(() => undoStack.value.length > 0);
  const canRedo = computed(() => redoStack.value.length > 0);

  function pushState(site: Site) {
    try {
      const serialized = JSON.stringify(site);
      // Avoid pushing duplicate identical states
      if (undoStack.value.length > 0 && undoStack.value[undoStack.value.length - 1] === serialized) {
        return;
      }
      undoStack.value.push(serialized);
      if (undoStack.value.length > MAX_HISTORY) {
        undoStack.value.shift();
      }
      // New action clears redo stack
      redoStack.value = [];
    } catch (err) {
      console.error("Failed to snapshot state for undo history", err);
    }
  }

  function undo(currentSite: Site): Site | null {
    if (!canUndo.value) return null;

    try {
      // Save current state into redo stack
      redoStack.value.push(JSON.stringify(currentSite));
      if (redoStack.value.length > MAX_HISTORY) {
        redoStack.value.shift();
      }

      // Pop state from undo stack
      const previousSerialized = undoStack.value.pop();
      if (!previousSerialized) return null;

      return JSON.parse(previousSerialized) as Site;
    } catch (err) {
      console.error("Failed to perform undo", err);
      return null;
    }
  }

  function redo(currentSite: Site): Site | null {
    if (!canRedo.value) return null;

    try {
      // Save current state into undo stack
      undoStack.value.push(JSON.stringify(currentSite));
      if (undoStack.value.length > MAX_HISTORY) {
        undoStack.value.shift();
      }

      // Pop state from redo stack
      const nextSerialized = redoStack.value.pop();
      if (!nextSerialized) return null;

      return JSON.parse(nextSerialized) as Site;
    } catch (err) {
      console.error("Failed to perform redo", err);
      return null;
    }
  }

  function clear() {
    undoStack.value = [];
    redoStack.value = [];
  }

  return {
    undoStack,
    redoStack,
    canUndo,
    canRedo,
    pushState,
    undo,
    redo,
    clear,
  };
});
