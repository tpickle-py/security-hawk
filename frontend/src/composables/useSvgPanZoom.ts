import { ref, type Ref } from "vue";
import { useEditorStore } from "@/stores/editorStore";

export function useSvgPanZoom(svgRef: Ref<SVGSVGElement | null>) {
  const editorStore = useEditorStore();
  const isDragging = ref(false);
  const dragStart = ref({ x: 0, y: 0 });
  const panStart = ref({ x: 0, y: 0 });

  function screenToSvg(clientX: number, clientY: number): { x: number; y: number } {
    if (!svgRef.value) return { x: 0, y: 0 };
    const rect = svgRef.value.getBoundingClientRect();
    const relX = clientX - rect.left;
    const relY = clientY - rect.top;

    // Apply inverse transform of pan & zoom
    const svgX = (relX - editorStore.panX) / editorStore.zoom;
    const svgY = (relY - editorStore.panY) / editorStore.zoom;
    return { x: svgX, y: svgY };
  }

  function onMouseDown(e: MouseEvent) {
    // Only pan on middle button or when pan tool is active or with spacebar
    if (e.button === 1 || editorStore.activeTool === "pan" || e.altKey) {
      isDragging.value = true;
      dragStart.value = { x: e.clientX, y: e.clientY };
      panStart.value = { x: editorStore.panX, y: editorStore.panY };
      e.preventDefault();
    }
  }

  function onMouseMove(e: MouseEvent) {
    if (isDragging.value) {
      const dx = e.clientX - dragStart.value.x;
      const dy = e.clientY - dragStart.value.y;
      editorStore.panX = panStart.value.x + dx;
      editorStore.panY = panStart.value.y + dy;
    }
  }

  function onMouseUp() {
    isDragging.value = false;
  }

  function onWheel(e: WheelEvent) {
    e.preventDefault();
    if (!svgRef.value) return;

    const rect = svgRef.value.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    const zoomFactor = e.deltaY < 0 ? 1.15 : 0.85;
    const newZoom = Math.min(Math.max(editorStore.zoom * zoomFactor, 0.1), 10.0);

    // Zoom centered on mouse pointer
    editorStore.panX = mouseX - (mouseX - editorStore.panX) * (newZoom / editorStore.zoom);
    editorStore.panY = mouseY - (mouseY - editorStore.panY) * (newZoom / editorStore.zoom);
    editorStore.zoom = newZoom;
  }

  return {
    isDragging,
    screenToSvg,
    onMouseDown,
    onMouseMove,
    onMouseUp,
    onWheel,
  };
}
