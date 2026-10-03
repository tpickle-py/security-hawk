export type EndpointType = "motion" | "door" | "window" | "camera" | "generic";

export interface ScalePoint {
  x: number;
  y: number;
}

export interface Scale {
  point1: ScalePoint;
  point2: ScalePoint;
  real_distance_m: number;
}

export interface BackgroundAsset {
  asset_id: string;
  filename: string;
  original_name?: string;
  url: string;
  x: number;
  y: number;
  width: number;
  height: number;
  rotation: number;
  locked: boolean;
}

export interface Coverage {
  type: "cone" | "area";
  angle: number;
  range: number;
}

export interface Endpoint {
  id: string;
  entity_id: string;
  device_id: string | null;
  type: EndpointType;
  x: number;
  y: number;
  rotation: number;
  label: string;
  companions: string[];
  cameras: string[];
  coverage: Coverage | null;
  stale_after: string | null;
  parent_id?: string | null; // Nested entity (attached to another endpoint)
  group_id?: string | null; // Grouped unit ID
  group_name?: string | null; // Grouped unit name (e.g. "Front Entrance Suite")
}

export interface SubArea {
  id: string;
  name: string;
  parent_area_id?: string | null; // Nested area (area within an area)
  x: number;
  y: number;
  width: number;
  height: number;
  color?: string;
}

export interface Shape {
  id: string;
  type: "wall" | "room" | "door" | "window" | "label";
  geometry: Record<string, unknown>;
  style: Record<string, unknown>;
}

export interface Floor {
  id: string;
  name: string;
  scale: Scale | null;
  background: BackgroundAsset | null;
  shapes: Shape[];
  sub_areas?: SubArea[];
  endpoints: Endpoint[];
}

export type FloorLike = Omit<Floor, "shapes">;

export interface Building {
  id: string;
  name: string;
  x: number;
  y: number;
  floors: Floor[];
}

export interface Site {
  schema_version: number;
  name: string;
  overview: FloorLike;
  buildings: Building[];
}

export interface EntityState {
  entity_id: string;
  state: string | null;
  attributes: Record<string, unknown>;
  last_changed: string | null;
}

export interface HAArea {
  area_id: string;
  name: string;
  picture?: string | null;
  aliases?: string[];
  entity_count?: number;
}

export interface HAEntity {
  entity_id: string;
  name: string;
  domain: string;
  device_id: string | null;
  area_id: string | null;
  area_name?: string | null;
  icon: string | null;
  platform?: string | null;
  state?: string | null;
  device_class?: string | null;
  friendly_name?: string | null;
}

