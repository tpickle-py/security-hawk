import { defineStore } from "pinia";
import { ref, computed } from "vue";
import type { ScalePoint } from "@/types/plan";

export type EditorTool = "select" | "pan" | "scale" | "place_endpoint" | "sub_area";

export const useEditorStore = defineStore("editor", () => {
  const mode = ref<"design" | "usage">("design");
  const activeTool = ref<EditorTool>("select");
  const selectedEndpointIds = ref<string[]>([]);

  // Backward compatibility single-select getter
  const selectedEndpointId = computed(() => selectedEndpointIds.value[0] || null);

  // Pan & Zoom
  const zoom = ref(1.0);
  const panX = ref(0);
  const panY = ref(0);

  // Scale calibration tool state
  const scalePoint1 = ref<ScalePoint | null>(null);
  const scalePoint2 = ref<ScalePoint | null>(null);
  const isSettingScale = ref(false);

  function setMode(m: "design" | "usage") {
    mode.value = m;
    if (m === "usage") {
      selectedEndpointIds.value = [];
      activeTool.value = "select";
    }
  }

  function setTool(tool: EditorTool) {
    activeTool.value = tool;
    if (tool !== "select") {
      selectedEndpointIds.value = [];
    }
    if (tool !== "scale") {
      scalePoint1.value = null;
      scalePoint2.value = null;
      isSettingScale.value = false;
    }
  }

  function selectEndpoint(id: string | null, multi = false) {
    if (!id) {
      selectedEndpointIds.value = [];
      return;
    }
    activeTool.value = "select";
    if (multi) {
      if (selectedEndpointIds.value.includes(id)) {
        selectedEndpointIds.value = selectedEndpointIds.value.filter((x) => x !== id);
      } else {
        selectedEndpointIds.value.push(id);
      }
    } else {
      selectedEndpointIds.value = [id];
    }
  }

  function selectAll(ids: string[]) {
    selectedEndpointIds.value = [...ids];
  }

  function clearSelection() {
    selectedEndpointIds.value = [];
  }

  function isEndpointSelected(id: string): boolean {
    return selectedEndpointIds.value.includes(id);
  }

  function resetView() {
    zoom.value = 1.0;
    panX.value = 0;
    panY.value = 0;
  }

  function zoomIn() {
    zoom.value = Math.min(zoom.value * 1.25, 8.0);
  }

  function zoomOut() {
    zoom.value = Math.max(zoom.value / 1.25, 0.2);
  }

  function startScaleCalibration() {
    activeTool.value = "scale";
    scalePoint1.value = null;
    scalePoint2.value = null;
    isSettingScale.value = true;
  }

  function addScalePoint(pt: ScalePoint) {
    if (!scalePoint1.value) {
      scalePoint1.value = pt;
    } else if (!scalePoint2.value) {
      scalePoint2.value = pt;
    }
  }

  function cancelScaleCalibration() {
    scalePoint1.value = null;
    scalePoint2.value = null;
    isSettingScale.value = false;
    activeTool.value = "select";
  }

  return {
    mode,
    activeTool,
    selectedEndpointIds,
    selectedEndpointId,
    zoom,
    panX,
    panY,
    scalePoint1,
    scalePoint2,
    isSettingScale,
    setMode,
    setTool,
    selectEndpoint,
    selectAll,
    clearSelection,
    isEndpointSelected,
    resetView,
    zoomIn,
    zoomOut,
    startScaleCalibration,
    addScalePoint,
    cancelScaleCalibration,
  };
});
