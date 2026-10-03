import { defineStore } from "pinia";
import { ref } from "vue";
import type { EntityState } from "@/types/plan";

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

  return {
    isConnected,
    states,
    lastEventTime,
    eventFeed,
    followActivityEnabled,
    highlightedEndpointId,
    activeCameraPopup,
    quietReturnSeconds,
    setConnected,
    handleInitialStates,
    handleStateChange,
    getState,
    highlightEndpoint,
    triggerCameraPopup,
    dismissCameraPopup,
    toggleFollowActivity,
    resetQuietReturn,
  };
});
