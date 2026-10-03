import type { Shape, Endpoint } from "@/types/plan";

export interface SnapResult {
  x: number;
  y: number;
  snapped: boolean;
  snapType: "vertex" | "grid" | "angle" | "none";
  targetPoint?: { x: number; y: number };
}

export function useSnapEngine() {
  const SNAP_DISTANCE = 14; // pixels in SVG coordinates
  const GRID_SIZE = 20;

  /**
   * Extract all snap-target vertices from shapes and endpoints.
   */
  function extractVertices(shapes: Shape[], endpoints: Endpoint[]): Array<{ x: number; y: number; label?: string }> {
    const vertices: Array<{ x: number; y: number; label?: string }> = [];

    // Endpoints
    for (const ep of endpoints) {
      vertices.push({ x: ep.x, y: ep.y, label: ep.label });
    }

    // Shapes
    for (const s of shapes) {
      if (s.type === "wall") {
        const geom = s.geometry as any;
        if (typeof geom.x1 === "number" && typeof geom.y1 === "number") {
          vertices.push({ x: geom.x1, y: geom.y1 });
        }
        if (typeof geom.x2 === "number" && typeof geom.y2 === "number") {
          vertices.push({ x: geom.x2, y: geom.y2 });
        }
      } else if (s.type === "room") {
        const geom = s.geometry as any;
        if (Array.isArray(geom.points)) {
          for (const pt of geom.points) {
            if (Array.isArray(pt) && pt.length >= 2) {
              vertices.push({ x: pt[0], y: pt[1] });
            }
          }
        }
      } else if (s.type === "label") {
        const geom = s.geometry as any;
        if (typeof geom.x === "number" && typeof geom.y === "number") {
          vertices.push({ x: geom.x, y: geom.y });
        }
      }
    }

    return vertices;
  }

  /**
   * Find closest vertex within snap threshold.
   */
  function snapToVertex(
    rawX: number,
    rawY: number,
    vertices: Array<{ x: number; y: number }>,
    threshold = SNAP_DISTANCE
  ): { x: number; y: number } | null {
    let closest: { x: number; y: number } | null = null;
    let minDist = threshold;

    for (const v of vertices) {
      const dist = Math.hypot(v.x - rawX, v.y - rawY);
      if (dist < minDist) {
        minDist = dist;
        closest = { x: v.x, y: v.y };
      }
    }

    return closest;
  }

  /**
   * Snap to nearest grid coordinate.
   */
  function snapToGrid(val: number, step = GRID_SIZE): number {
    return Math.round(val / step) * step;
  }

  /**
   * Snap relative angle from origin point (0°, 45°, 90°, 135°, 180°, etc.).
   */
  function snapAngle(
    originX: number,
    originY: number,
    targetX: number,
    targetY: number
  ): { x: number; y: number } {
    const dx = targetX - originX;
    const dy = targetY - originY;
    const distance = Math.hypot(dx, dy);
    if (distance < 1) return { x: targetX, y: targetY };

    let angle = Math.atan2(dy, dx); // radians
    // Snap to 45 degree increments (pi / 4)
    const step = Math.PI / 4;
    angle = Math.round(angle / step) * step;

    return {
      x: Math.round(originX + distance * Math.cos(angle)),
      y: Math.round(originY + distance * Math.sin(angle)),
    };
  }

  /**
   * Combined snap resolver:
   * 1. Priority to existing vertices (magnetic snap)
   * 2. If origin provided and shiftKey held, lock to orthogonal / 45° angle
   * 3. Fallback to grid snap
   */
  function snapCoordinate(
    rawX: number,
    rawY: number,
    vertices: Array<{ x: number; y: number }>,
    options?: {
      originPoint?: { x: number; y: number } | null;
      shiftKey?: boolean;
      gridEnabled?: boolean;
    }
  ): SnapResult {
    const { originPoint = null, shiftKey = false, gridEnabled = true } = options || {};

    let currentX = rawX;
    let currentY = rawY;

    // Angle lock if Shift is held and we have an origin
    if (shiftKey && originPoint) {
      const angled = snapAngle(originPoint.x, originPoint.y, currentX, currentY);
      currentX = angled.x;
      currentY = angled.y;
    }

    // Vertex snap has highest priority
    const vertexMatch = snapToVertex(currentX, currentY, vertices);
    if (vertexMatch) {
      return {
        x: vertexMatch.x,
        y: vertexMatch.y,
        snapped: true,
        snapType: "vertex",
        targetPoint: vertexMatch,
      };
    }

    // Grid snap
    if (gridEnabled) {
      const gx = snapToGrid(currentX);
      const gy = snapToGrid(currentY);
      const dist = Math.hypot(gx - currentX, gy - currentY);
      if (dist <= SNAP_DISTANCE) {
        return {
          x: gx,
          y: gy,
          snapped: true,
          snapType: "grid",
          targetPoint: { x: gx, y: gy },
        };
      }
    }

    // No snap
    return {
      x: Math.round(currentX),
      y: Math.round(currentY),
      snapped: false,
      snapType: "none",
    };
  }

  return {
    SNAP_DISTANCE,
    GRID_SIZE,
    extractVertices,
    snapToVertex,
    snapToGrid,
    snapAngle,
    snapCoordinate,
  };
}
