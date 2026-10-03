<script setup lang="ts">
import { useEditorStore } from "@/stores/editorStore";
import type { Shape, WallGeometry, RoomGeometry, LabelGeometry } from "@/types/plan";

const props = defineProps<{
  shapes: Shape[];
  activeSnapPoint?: { x: number; y: number; snapType: string } | null;
  cursorPoint?: { x: number; y: number } | null;
}>();

const emit = defineEmits<{
  (e: "select-shape", shapeId: string): void;
  (e: "wall-click", wallId: string, clickPoint: { x: number; y: number }): void;
}>();

const editorStore = useEditorStore();

// Helper to compute room polygon points string and centroid for label
function getPolygonPoints(geom: RoomGeometry): string {
  if (!geom.points || geom.points.length === 0) return "";
  return geom.points.map((pt) => `${pt[0]},${pt[1]}`).join(" ");
}

function getPolygonCentroid(geom: RoomGeometry): { x: number; y: number } {
  if (!geom.points || geom.points.length === 0) return { x: 0, y: 0 };
  let sumX = 0;
  let sumY = 0;
  for (const pt of geom.points) {
    sumX += pt[0];
    sumY += pt[1];
  }
  return {
    x: Math.round(sumX / geom.points.length),
    y: Math.round(sumY / geom.points.length),
  };
}

// Wall rendering with openings (doors & windows)
interface WallSegment {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}

interface RenderedOpening {
  id: string;
  type: "door" | "window";
  x: number;
  y: number;
  angleDeg: number;
  width: number;
}

function processWallGeometry(geom: WallGeometry) {
  const { x1, y1, x2, y2, openings = [] } = geom;
  const dx = x2 - x1;
  const dy = y2 - y1;
  const totalLength = Math.hypot(dx, dy);

  if (totalLength === 0) {
    return { segments: [], openingsList: [] };
  }

  const ux = dx / totalLength;
  const uy = dy / totalLength;
  const angleDeg = (Math.atan2(dy, dx) * 180) / Math.PI;

  if (openings.length === 0) {
    return {
      segments: [{ x1, y1, x2, y2 }],
      openingsList: [],
    };
  }

  // Sort openings along wall by offset
  const sorted = [...openings].sort((a, b) => a.offset - b.offset);
  const segments: WallSegment[] = [];
  const openingsList: RenderedOpening[] = [];

  let currentDist = 0;
  for (const op of sorted) {
    const opStart = Math.max(0, op.offset);
    const opEnd = Math.min(totalLength, op.offset + op.width);

    if (opStart > currentDist) {
      segments.push({
        x1: x1 + ux * currentDist,
        y1: y1 + uy * currentDist,
        x2: x1 + ux * opStart,
        y2: y1 + uy * opStart,
      });
    }

    // Opening center point
    const midOffset = (opStart + opEnd) / 2;
    openingsList.push({
      id: op.id,
      type: op.type,
      x: x1 + ux * midOffset,
      y: y1 + uy * midOffset,
      angleDeg,
      width: op.width,
    });

    currentDist = Math.max(currentDist, opEnd);
  }

  if (currentDist < totalLength) {
    segments.push({
      x1: x1 + ux * currentDist,
      y1: y1 + uy * currentDist,
      x2,
      y2,
    });
  }

  return { segments, openingsList };
}

function handleWallClick(shape: Shape, e: MouseEvent) {
  if (editorStore.activeTool === "door" || editorStore.activeTool === "window") {
    e.stopPropagation();
    emit("wall-click", shape.id, { x: props.cursorPoint?.x || 0, y: props.cursorPoint?.y || 0 });
    return;
  }
  emit("select-shape", shape.id);
}
</script>

<template>
  <g class="shapes-layer">
    <!-- 1. Room Polygons Layer (rendered beneath walls) -->
    <g class="rooms-group">
      <template v-for="shape in shapes" :key="shape.id">
        <g v-if="shape.type === 'room'" class="room-shape" @click.stop="emit('select-shape', shape.id)">
          <polygon
            :points="getPolygonPoints(shape.geometry as RoomGeometry)"
            :fill="(shape.style?.fill as string) || 'rgba(99, 102, 241, 0.12)'"
            :stroke="(shape.style?.stroke as string) || '#6366f1'"
            :stroke-width="editorStore.selectedShapeId === shape.id ? 2.5 : 1.5"
            :class="{ selected: editorStore.selectedShapeId === shape.id }"
          />
          <!-- Room Name Label -->
          <text
            v-if="(shape.geometry as RoomGeometry).name"
            :x="getPolygonCentroid(shape.geometry as RoomGeometry).x"
            :y="getPolygonCentroid(shape.geometry as RoomGeometry).y"
            class="room-label"
          >
            {{ (shape.geometry as RoomGeometry).name }}
          </text>
        </g>
      </template>
    </g>

    <!-- 2. Walls Layer with Cutouts -->
    <g class="walls-group">
      <template v-for="shape in shapes" :key="shape.id">
        <g v-if="shape.type === 'wall'" class="wall-shape" @click="handleWallClick(shape, $event)">
          <!-- Processed Wall Segments -->
          <line
            v-for="(seg, idx) in processWallGeometry(shape.geometry as WallGeometry).segments"
            :key="idx"
            :x1="seg.x1"
            :y1="seg.y1"
            :x2="seg.x2"
            :y2="seg.y2"
            :stroke="(shape.style?.stroke as string) || '#94a3b8'"
            :stroke-width="(shape.geometry as WallGeometry).thickness || 8"
            stroke-linecap="round"
            :class="{ selected: editorStore.selectedShapeId === shape.id }"
          />

          <!-- Openings (Door swing arcs / Window lines) -->
          <g
            v-for="op in processWallGeometry(shape.geometry as WallGeometry).openingsList"
            :key="op.id"
            :transform="`translate(${op.x}, ${op.y}) rotate(${op.angleDeg})`"
          >
            <!-- Door: leaf + swing arc -->
            <template v-if="op.type === 'door'">
              <!-- Dotted 90-degree swing arc -->
              <path
                :d="`M ${-op.width / 2} 0 A ${op.width} ${op.width} 0 0 1 ${-op.width / 2 + op.width * 0.707} ${-op.width * 0.707}`"
                fill="none"
                stroke="#6366f1"
                stroke-width="1.2"
                stroke-dasharray="3 3"
              />
              <!-- Door leaf -->
              <line
                :x1="-op.width / 2"
                y1="0"
                :x2="-op.width / 2 + op.width * 0.707"
                :y2="-op.width * 0.707"
                stroke="#818cf8"
                stroke-width="2.5"
              />
            </template>

            <!-- Window: dual frame lines with mullion -->
            <template v-else-if="op.type === 'window'">
              <line
                :x1="-op.width / 2"
                y1="0"
                :x2="op.width / 2"
                y2="0"
                stroke="#38bdf8"
                stroke-width="3"
              />
              <line :x1="-op.width / 2" y1="-4" :x2="-op.width / 2" y2="4" stroke="#38bdf8" stroke-width="2" />
              <line :x1="op.width / 2" y1="-4" :x2="op.width / 2" y2="4" stroke="#38bdf8" stroke-width="2" />
            </template>
          </g>
        </g>
      </template>
    </g>

    <!-- 3. Architectural Text Labels -->
    <g class="labels-group">
      <template v-for="shape in shapes" :key="shape.id">
        <g v-if="shape.type === 'label'" class="label-shape" @click.stop="emit('select-shape', shape.id)">
          <text
            :x="(shape.geometry as LabelGeometry).x"
            :y="(shape.geometry as LabelGeometry).y"
            :font-size="(shape.geometry as LabelGeometry).fontSize || 13"
            :fill="(shape.style?.color as string) || '#cbd5e1'"
            class="arch-label"
            :class="{ selected: editorStore.selectedShapeId === shape.id }"
          >
            {{ (shape.geometry as LabelGeometry).text }}
          </text>
        </g>
      </template>
    </g>

    <!-- 4. Active Drawing Previews -->
    <g class="drawing-preview" v-if="editorStore.drawingPoints.length > 0 && cursorPoint">
      <!-- Active Wall Preview Line -->
      <template v-if="editorStore.activeTool === 'wall'">
        <line
          :x1="editorStore.drawingPoints[0].x"
          :y1="editorStore.drawingPoints[0].y"
          :x2="cursorPoint.x"
          :y2="cursorPoint.y"
          :stroke="editorStore.activeWallColor"
          :stroke-width="editorStore.activeWallThickness"
          stroke-dasharray="6 4"
          stroke-linecap="round"
        />
        <!-- Dimension readout badge -->
        <g :transform="`translate(${(editorStore.drawingPoints[0].x + cursorPoint.x) / 2}, ${(editorStore.drawingPoints[0].y + cursorPoint.y) / 2 - 12})`">
          <rect x="-24" y="-10" width="48" height="20" rx="4" fill="#0f172a" stroke="#6366f1" stroke-width="1" />
          <text x="0" y="4" class="dimension-text">
            {{ Math.round(Math.hypot(cursorPoint.x - editorStore.drawingPoints[0].x, cursorPoint.y - editorStore.drawingPoints[0].y)) }}px
          </text>
        </g>
      </template>

      <!-- Active Room Preview Polygon -->
      <template v-else-if="editorStore.activeTool === 'room'">
        <polyline
          :points="[...editorStore.drawingPoints, cursorPoint].map((p) => `${p.x},${p.y}`).join(' ')"
          fill="rgba(99, 102, 241, 0.08)"
          stroke="#6366f1"
          stroke-width="2"
          stroke-dasharray="4 4"
        />
        <!-- Node markers at placed points -->
        <circle
          v-for="(p, i) in editorStore.drawingPoints"
          :key="i"
          :cx="p.x"
          :cy="p.y"
          r="4"
          fill="#6366f1"
          stroke="#ffffff"
          stroke-width="1.5"
        />
      </template>
    </g>

    <!-- 5. Magnetic Snap Indicator -->
    <g v-if="activeSnapPoint && activeSnapPoint.snapType !== 'none'" class="snap-indicator">
      <circle
        :cx="activeSnapPoint.x"
        :cy="activeSnapPoint.y"
        r="6"
        fill="none"
        :stroke="activeSnapPoint.snapType === 'vertex' ? '#10b981' : activeSnapPoint.snapType === 'angle' ? '#f59e0b' : '#6366f1'"
        stroke-width="2"
        class="pulse-ring"
      />
      <circle
        :cx="activeSnapPoint.x"
        :cy="activeSnapPoint.y"
        r="2"
        :fill="activeSnapPoint.snapType === 'vertex' ? '#10b981' : activeSnapPoint.snapType === 'angle' ? '#f59e0b' : '#6366f1'"
      />
    </g>
  </g>
</template>

<style scoped>
.shapes-layer {
  pointer-events: visiblePainted;
}

.room-shape {
  cursor: pointer;
  transition: opacity 0.15s ease;
}

.room-shape:hover polygon {
  fill-opacity: 0.25;
}

.room-label {
  fill: #e2e8f0;
  font-size: 13px;
  font-weight: 600;
  text-anchor: middle;
  dominant-baseline: central;
  letter-spacing: 0.5px;
  pointer-events: none;
  filter: drop-shadow(0 1px 3px rgba(0, 0, 0, 0.8));
}

.wall-shape {
  cursor: pointer;
}

.wall-shape line.selected {
  stroke: #6366f1 !important;
  filter: drop-shadow(0 0 6px rgba(99, 102, 241, 0.6));
}

.arch-label {
  font-family: inherit;
  font-weight: 500;
  letter-spacing: 0.3px;
  cursor: pointer;
  filter: drop-shadow(0 1px 2px rgba(0, 0, 0, 0.6));
}

.arch-label.selected {
  fill: #6366f1 !important;
  font-weight: 700;
}

.dimension-text {
  fill: #cbd5e1;
  font-size: 10px;
  font-family: var(--font-mono, monospace);
  font-weight: 600;
  text-anchor: middle;
  pointer-events: none;
}

.pulse-ring {
  animation: snapPulse 1.2s ease-in-out infinite;
}

@keyframes snapPulse {
  0% {
    r: 5;
    opacity: 1;
  }
  50% {
    r: 9;
    opacity: 0.5;
  }
  100% {
    r: 5;
    opacity: 1;
  }
}
</style>
