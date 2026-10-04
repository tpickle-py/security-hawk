import { defineStore } from "pinia";
import { ref } from "vue";
import type { EntityState, DockPositions, DockCorner } from "@/types/plan";

export const DEFAULT_DOCK_POSITIONS: DockPositions = {
  activity_feed: "bottom-left",
  nav_controls: "bottom-right",
};

export interface LiveEvent {
  id: string;
  entity_id: string;
  from_state: string | null;
  to_state: string | null;
  timestamp: Date;
  attributes: Record<string, unknown>;
  friendly_name?: string;
  domain: string;
}

export interface CameraPopupInfo {
  cameraEntityId: string;
  triggeredBy: string;
  label: string;
  remainingSeconds: number;
}

export interface TraversalNode {
  id: string;
  endpointId: string;
  entityId: string;
  label: string;
  x: number;
  y: number;
  timestamp: number;
  sequenceIndex: number;
  elapsedSeconds: number;
}

export interface TraversalTrail {
  id: string;
  floorId: string | null;
  startTime: number;
  lastUpdatedTime: number;
  nodes: TraversalNode[];
}

export const useLiveStore = defineStore("live", () => {
  const isConnected = ref(false);
  const states = ref<Record<string, EntityState>>({});
  const lastEventTime = ref<Date | null>(null);

  // Live Event Feed (last 50 events)
  const eventFeed = ref<LiveEvent[]>([]);

  // Follow-Activity Mode
  const followActivityEnabled = ref(false);

  // Highlighted endpoint for visual jump/focus
  const highlightedEndpointId = ref<string | null>(null);

  // Linked Camera Auto-Popup Modal
  const activeCameraPopup = ref<CameraPopupInfo | null>(null);
  let cameraTimer: number | null = null;

  // Quiet Return Timer (120s by default)
  let quietReturnTimer: number | null = null;
  const quietReturnSeconds = ref(120);

  // Active Connected Screens / Viewers
  const viewerCount = ref(1);
  const totalViewers = ref(1);

  // Docked Menus & Overlays Layout Positions
  const dockPositions = ref<DockPositions>(getInitialDockPositions());

  function getInitialDockPositions(): DockPositions {
    try {
      const saved = localStorage.getItem("sh_dock_positions");
      if (saved) {
        const parsed = JSON.parse(saved);
        return {
          activity_feed: parsed.activity_feed || "bottom-left",
          nav_controls: parsed.nav_controls || "bottom-right",
        };
      }
    } catch {
      // ignore
    }
    return { ...DEFAULT_DOCK_POSITIONS };
  }

  function setDockPosition(menu: "activity_feed" | "nav_controls", corner: DockCorner) {
    dockPositions.value = {
      ...dockPositions.value,
      [menu]: corner,
    };
    try {
      localStorage.setItem("sh_dock_positions", JSON.stringify(dockPositions.value));
    } catch {}
  }

  function cycleDockPosition(menu: "activity_feed" | "nav_controls") {
    const corners: DockCorner[] = ["bottom-left", "bottom-right", "top-right", "top-left"];
    const current = dockPositions.value[menu];
    const nextIdx = (corners.indexOf(current) + 1) % corners.length;
    setDockPosition(menu, corners[nextIdx]);
  }

  function resetDockPositions() {
    dockPositions.value = { ...DEFAULT_DOCK_POSITIONS };
    try {
      localStorage.setItem("sh_dock_positions", JSON.stringify(DEFAULT_DOCK_POSITIONS));
    } catch {}
  }

  function setDockPositionsFromSettings(positions?: DockPositions | null) {
    if (!positions) return;
    dockPositions.value = {
      activity_feed: positions.activity_feed || "bottom-left",
      nav_controls: positions.nav_controls || "bottom-right",
    };
    try {
      localStorage.setItem("sh_dock_positions", JSON.stringify(dockPositions.value));
    } catch {}
  }

  function setViewerCount(count: number, total?: number) {
    if (typeof count === "number" && count >= 0) {
      viewerCount.value = Math.max(1, count);
    }
    if (typeof total === "number" && total >= 0) {
      totalViewers.value = Math.max(1, total);
    }
  }

  function setConnected(connected: boolean) {
    isConnected.value = connected;
  }

  function handleInitialStates(initialStates: Record<string, any>) {
    const map: Record<string, EntityState> = {};
    for (const [entityId, data] of Object.entries(initialStates)) {
      map[entityId] = {
        entity_id: entityId,
        state: data.state ?? null,
        attributes: data.attributes || {},
        last_changed: data.last_changed || null,
      };
    }
    states.value = map;
    lastEventTime.value = new Date();
  }

  function handleStateChange(entityId: string, newState: any) {
    if (!newState) {
      delete states.value[entityId];
      return;
    }

    const prevState = states.value[entityId]?.state ?? null;
    const nextState = newState.state ?? null;

    states.value[entityId] = {
      entity_id: entityId,
      state: nextState,
      attributes: newState.attributes || {},
      last_changed: newState.last_changed || null,
    };
    lastEventTime.value = new Date();

    // If state value changed, record into Event Feed
    if (prevState !== nextState && nextState !== null) {
      const domain = entityId.split(".")[0] || "generic";
      const friendlyName = newState.attributes?.friendly_name || entityId;

      const event: LiveEvent = {
        id: "evt_" + Math.random().toString(36).substring(2, 9),
        entity_id: entityId,
        from_state: prevState,
        to_state: nextState,
        timestamp: new Date(),
        attributes: newState.attributes || {},
        friendly_name: friendlyName,
        domain,
      };

      // Keep newest 50 events
      eventFeed.value.unshift(event);
      if (eventFeed.value.length > 50) {
        eventFeed.value.pop();
      }
    }
  }

  function getState(entityId: string): EntityState | undefined {
    return states.value[entityId];
  }

  function highlightEndpoint(id: string) {
    highlightedEndpointId.value = id;
    window.setTimeout(() => {
      if (highlightedEndpointId.value === id) {
        highlightedEndpointId.value = null;
      }
    }, 4000);
  }

  function triggerCameraPopup(cameraEntityId: string, triggeredBy: string, label: string) {
    if (cameraTimer) clearInterval(cameraTimer);

    activeCameraPopup.value = {
      cameraEntityId,
      triggeredBy,
      label,
      remainingSeconds: 30,
    };

    cameraTimer = window.setInterval(() => {
      if (!activeCameraPopup.value) {
        if (cameraTimer) clearInterval(cameraTimer);
        return;
      }
      activeCameraPopup.value.remainingSeconds -= 1;
      if (activeCameraPopup.value.remainingSeconds <= 0) {
        dismissCameraPopup();
      }
    }, 1000);
  }

  function dismissCameraPopup() {
    activeCameraPopup.value = null;
    if (cameraTimer) {
      clearInterval(cameraTimer);
      cameraTimer = null;
    }
  }

  function toggleFollowActivity() {
    followActivityEnabled.value = !followActivityEnabled.value;
  }

  function resetQuietReturn(onQuietReturnCallback: () => void) {
    if (quietReturnTimer) clearTimeout(quietReturnTimer);
    if (!followActivityEnabled.value) return;

    quietReturnTimer = window.setTimeout(() => {
      onQuietReturnCallback();
    }, quietReturnSeconds.value * 1000);
  }

  // Spatio-Temporal Motion Traversal Trail
  const motionTrailsEnabled = ref(true);
  const activeTrail = ref<TraversalTrail | null>(null);
  const traversalWindowSeconds = ref(45);
  let trailFadeTimer: number | null = null;

  function toggleMotionTrails() {
    motionTrailsEnabled.value = !motionTrailsEnabled.value;
    if (!motionTrailsEnabled.value) {
      activeTrail.value = null;
    }
  }

  function clearMotionTrails() {
    activeTrail.value = null;
    if (trailFadeTimer) {
      clearTimeout(trailFadeTimer);
      trailFadeTimer = null;
    }
  }

  function recordTraversalNode(
    endpoint: { id: string; entity_id: string; label?: string; x: number; y: number },
    floorId: string | null
  ) {
    if (!motionTrailsEnabled.value) return;

    const now = Date.now();
    const windowMs = traversalWindowSeconds.value * 1000;

    if (trailFadeTimer) clearTimeout(trailFadeTimer);
    trailFadeTimer = window.setTimeout(() => {
      activeTrail.value = null;
    }, windowMs);

    if (
      activeTrail.value &&
      activeTrail.value.floorId === floorId &&
      now - activeTrail.value.lastUpdatedTime <= windowMs
    ) {
      const nodes = activeTrail.value.nodes;
      const lastNode = nodes[nodes.length - 1];

      if (lastNode && lastNode.endpointId === endpoint.id && now - lastNode.timestamp < 2500) {
        return;
      }

      const firstTime = nodes[0]?.timestamp || now;
      const elapsedSec = Math.round((now - firstTime) / 1000);

      nodes.push({
        id: "tnode_" + Math.random().toString(36).substring(2, 8),
        endpointId: endpoint.id,
        entityId: endpoint.entity_id,
        label: endpoint.label || endpoint.entity_id,
        x: endpoint.x,
        y: endpoint.y,
        timestamp: now,
        sequenceIndex: nodes.length + 1,
        elapsedSeconds: elapsedSec,
      });

      activeTrail.value.lastUpdatedTime = now;
      return;
    }

    activeTrail.value = {
      id: "trail_" + Math.random().toString(36).substring(2, 8),
      floorId,
      startTime: now,
      lastUpdatedTime: now,
      nodes: [
        {
          id: "tnode_" + Math.random().toString(36).substring(2, 8),
          endpointId: endpoint.id,
          entityId: endpoint.entity_id,
          label: endpoint.label || endpoint.entity_id,
          x: endpoint.x,
          y: endpoint.y,
          timestamp: now,
          sequenceIndex: 1,
          elapsedSeconds: 0,
        },
      ],
    };
  }

  return {
    isConnected,
    states,
    lastEventTime,
    eventFeed,
    followActivityEnabled,
    highlightedEndpointId,
    activeCameraPopup,
    quietReturnSeconds,
    motionTrailsEnabled,
    activeTrail,
    viewerCount,
    totalViewers,
    dockPositions,
    setDockPosition,
    cycleDockPosition,
    resetDockPositions,
    setDockPositionsFromSettings,
    setViewerCount,
    setConnected,
    handleInitialStates,
    handleStateChange,
    getState,
    highlightEndpoint,
    triggerCameraPopup,
    dismissCameraPopup,
    toggleFollowActivity,
    resetQuietReturn,
    toggleMotionTrails,
    clearMotionTrails,
    recordTraversalNode,
  };
});
