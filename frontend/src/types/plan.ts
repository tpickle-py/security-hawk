export type EndpointType = "motion" | "door" | "window" | "camera" | "generic" | "composite";

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

export interface WallOpening {
  id: string;
  type: "door" | "window";
  offset: number; // offset in px along wall vector from start point
  width: number;  // width of opening in px
  swingDirection?: "left" | "right"; // for doors
  openPercent?: number; // 0 = closed, 100 = open
}

export interface WallGeometry {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  thickness?: number; // default 8px
  openings?: WallOpening[];
}

export interface RoomGeometry {
  points: Array<[number, number]>;
  name?: string;
}

export interface LabelGeometry {
  x: number;
  y: number;
  text: string;
  fontSize?: number;
  rotation?: number;
}

export interface ShapeStyle {
  stroke?: string;
  strokeWidth?: number;
  fill?: string;
  fillOpacity?: number;
  color?: string;
  fontSize?: number;
  fontFamily?: string;
}

export interface Shape {
  id: string;
  type: "wall" | "room" | "door" | "window" | "label";
  geometry: WallGeometry | RoomGeometry | LabelGeometry | Record<string, unknown>;
  style: ShapeStyle | Record<string, unknown>;
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

export type FloorLike = Omit<Floor, "shapes"> & { shapes?: Shape[] };

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

export interface RuleCondition {
  entity_id: string;
  state?: string;
  attribute?: string;
  operator?: "eq" | "neq" | "gt" | "lt";
  value?: unknown;
}

export interface RuleServiceCall {
  domain: string;
  service: string;
  service_data?: Record<string, unknown>;
}

export interface ActionPluginField {
  name: string;
  label: string;
  type: "text" | "number" | "password" | "textarea" | "select" | "json";
  required?: boolean;
  placeholder?: string;
  default?: unknown;
  options?: Array<{ label: string; value: string }>;
}

export interface ActionPlugin {
  type: string;
  name: string;
  description: string;
  icon: string;
  fields: ActionPluginField[];
}

export interface RuleAction {
  id?: string;
  type: string;
  config: Record<string, any>;
  enabled?: boolean;
}

export interface CompositeRule {
  id: string;
  name: string;
  enabled: boolean;
  logic: "ALL" | "ANY";
  time_window_seconds: number;
  reset_seconds: number;
  device_class?: string;
  output_entity_id?: string;
  conditions: RuleCondition[];
  actions?: RuleAction[];
  linked_cameras?: string[];
  service_call?: RuleServiceCall;
}

export interface MqttSettings {
  enabled: boolean;
  host: string;
  port: number;
  username?: string;
  password?: string;
  topic_prefix: string;
  ha_discovery: boolean;
}

export interface EmailSettings {
  smtp_host?: string;
  smtp_port?: number;
  smtp_user?: string;
  smtp_password?: string;
  smtp_from?: string;
  default_to?: string;
  smtp_use_tls?: boolean;
}

export interface WhatsAppSettings {
  provider?: string;
  default_phone?: string;
  api_key?: string;
  account_sid?: string;
  from_phone?: string;
  webhook_url?: string;
}

export interface NotificationSettings {
  email?: EmailSettings;
  whatsapp?: WhatsAppSettings;
}

export interface AppSettings {
  quiet_return_seconds: number;
  auto_dismiss_camera_seconds: number;
  default_view: "overview" | "floor";
  mqtt: MqttSettings;
  helpers: {
    auto_register_synthetic_sensors: boolean;
    prefix: string;
  };
  notifications?: NotificationSettings;
  ignored_entities?: string[];
  ignored_domains?: string[];
}

export interface KioskStatus {
  kiosk_enabled: boolean;
  kiosk_port: number;
  kiosk_token: string;
  active_viewers: {
    total_viewers: number;
    kiosk_viewers: number;
    standard_viewers: number;
    by_plan: Record<string, number>;
  };
}


