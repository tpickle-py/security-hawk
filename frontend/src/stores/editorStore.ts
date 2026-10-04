import { defineStore } from "pinia";
import { ref, computed } from "vue";
import type { ScalePoint } from "@/types/plan";

export type EditorTool =
  | "select"
  | "pan"
  | "scale"
  | "place_endpoint"
  | "sub_area"
  | "wall"
  | "room"
  | "door"
  | "window"
  | "label";

export type ViewportPreset =
  | "freeform"
  | "phone_portrait"
  | "phone_landscape"
  | "tablet"
  | "tablet_wide"
  | "tv"
  | "ultrawide";

export interface ViewportConfig {
  id: ViewportPreset;
  label: string;
  icon: string;
  aspectRatio: string;
  width: number;
  height: number;
}

export const VIEWPORT_CONFIGS: Record<ViewportPreset, ViewportConfig> = {
  freeform: {
    id: "freeform",
    label: "Freeform Canvas",
    icon: "📐",
    aspectRatio: "Full",
    width: 0,
    height: 0,
  },
  phone_portrait: {
    id: "phone_portrait",
    label: "Phone (Portrait 9:16)",
    icon: "📱",
    aspectRatio: "9:16",
    width: 390,
    height: 844,
  },
  phone_landscape: {
    id: "phone_landscape",
    label: "Phone (Landscape 16:9)",
    icon: "📱",
    aspectRatio: "16:9",
    width: 844,
    height: 390,
  },
  tablet: {
    id: "tablet",
    label: "Tablet (iPad 4:3)",
    icon: "📟",
    aspectRatio: "4:3",
    width: 1024,
    height: 768,
  },
  tablet_wide: {
    id: "tablet_wide",
    label: "Wall Tablet (16:10)",
    icon: "📟",
    aspectRatio: "16:10",
    width: 1280,
    height: 800,
  },
  tv: {
    id: "tv",
    label: "TV / Monitor (16:9)",
    icon: "📺",
    aspectRatio: "16:9",
    width: 1920,
    height: 1080,
  },
  ultrawide: {
    id: "ultrawide",
    label: "Ultrawide (21:9)",
    icon: "🖥️",
    aspectRatio: "21:9",
    width: 2560,
    height: 1080,
  },
};

export const useEditorStore = defineStore("editor", () => {
  const mode = ref<"design" | "usage">("design");
  const activeTool = ref<EditorTool>("select");
  const selectedEndpointIds = ref<string[]>([]);
  const selectedShapeId = ref<string | null>(null);

  // Viewport simulator
  const activeViewport = ref<ViewportPreset>("freeform");
  const showViewportGuides = ref(true);

  // Backward compatibility single-select getter
  const selectedEndpointId = computed(() => selectedEndpointIds.value[0] || null);

  // Active drawing state
  const drawingPoints = ref<Array<{ x: number; y: number }>>([]);
  const activeWallThickness = ref<number>(8);
  const activeWallColor = ref<string>("#94a3b8");
  const activeRoomFill = ref<string>("rgba(99, 102, 241, 0.12)");
  const activeRoomStroke = ref<string>("#6366f1");

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
      selectedShapeId.value = null;
      activeTool.value = "select";
      drawingPoints.value = [];
    }
  }

  function setTool(tool: EditorTool) {
    activeTool.value = tool;
    drawingPoints.value = [];
    if (tool !== "select") {
      selectedEndpointIds.value = [];
      selectedShapeId.value = null;
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

  function selectShape(id: string | null) {
    selectedShapeId.value = id;
    if (id) {
      selectedEndpointIds.value = [];
      activeTool.value = "select";
    }
  }

  function clearSelection() {
    selectedEndpointIds.value = [];
    selectedShapeId.value = null;
  }

  function cancelScaleCalibration() {
    scalePoint1.value = null;
    scalePoint2.value = null;
    isSettingScale.value = false;
    activeTool.value = "select";
  }

  function setViewport(preset: ViewportPreset) {
    activeViewport.value = preset;
  }

  function fitToView(
    containerWidth: number,
    containerHeight: number,
    contentBounds?: { minX: number; maxX: number; minY: number; maxY: number }
  ) {
    if (!contentBounds || contentBounds.minX === Infinity) {
      zoom.value = 1.0;
      panX.value = 0;
      panY.value = 0;
      return;
    }

    const contentW = Math.max(contentBounds.maxX - contentBounds.minX, 100);
    const contentH = Math.max(contentBounds.maxY - contentBounds.minY, 100);
    const padding = 60;

    const availW = Math.max(containerWidth - padding * 2, 100);
    const availH = Math.max(containerHeight - padding * 2, 100);
    const scaleX = availW / contentW;
    const scaleY = availH / contentH;
    const newZoom = Math.min(Math.max(Math.min(scaleX, scaleY), 0.15), 4.0);

    const contentCenterX = (contentBounds.minX + contentBounds.maxX) / 2;
    const contentCenterY = (contentBounds.minY + contentBounds.maxY) / 2;

    zoom.value = Number(newZoom.toFixed(3));
    panX.value = Math.round(containerWidth / 2 - contentCenterX * newZoom);
    panY.value = Math.round(containerHeight / 2 - contentCenterY * newZoom);
  }

  return {
    mode,
    activeTool,
    selectedEndpointIds,
    selectedEndpointId,
    selectedShapeId,
    activeViewport,
    showViewportGuides,
    drawingPoints,
    activeWallThickness,
    activeWallColor,
    activeRoomFill,
    activeRoomStroke,
    zoom,
    panX,
    panY,
    scalePoint1,
    scalePoint2,
    isSettingScale,
    setMode,
    setTool,
    setViewport,
    fitToView,
    selectEndpoint,
    selectAll,
    selectShape,
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
