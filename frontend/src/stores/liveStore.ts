import { defineStore } from "pinia";
import { ref } from "vue";
import type { EntityState } from "@/types/plan";

export const useLiveStore = defineStore("live", () => {
  const isConnected = ref(false);
  const states = ref<Record<string, EntityState>>({});
  const lastEventTime = ref<Date | null>(null);

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

    states.value[entityId] = {
      entity_id: entityId,
      state: newState.state ?? null,
      attributes: newState.attributes || {},
      last_changed: newState.last_changed || null,
    };
    lastEventTime.value = new Date();
  }

  function getState(entityId: string): EntityState | undefined {
    return states.value[entityId];
  }

  return {
    isConnected,
    states,
    lastEventTime,
    setConnected,
    handleInitialStates,
    handleStateChange,
    getState,
  };
});
