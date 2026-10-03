import { defineStore } from "pinia";
import { ref, computed } from "vue";
import type { HAEntity, HAArea, EndpointType } from "@/types/plan";
import { api } from "@/services/api";

export const useEntityStore = defineStore("entity", () => {
  const entities = ref<HAEntity[]>([]);
  const areas = ref<HAArea[]>([]);
  const unassignedCount = ref(0);
  const isLoading = ref(false);
  const error = ref<string | null>(null);

  const searchQuery = ref("");
  const selectedDomain = ref("");
  const selectedAreaId = ref("");
  const filterUnassignedOnly = ref(false);

  const unassignedEntities = computed(() => {
    return entities.value.filter((e) => !e.area_id);
  });

  async function fetchAreas() {
    try {
      const res = await api.listAreas();
      areas.value = res.areas;
      unassignedCount.value = res.unassigned_entities_count;
    } catch (e: any) {
      console.warn("Could not load areas:", e.message);
    }
  }

  async function fetchEntities(
    query = searchQuery.value,
    domain = selectedDomain.value,
    areaId = selectedAreaId.value,
    unassignedOnly = filterUnassignedOnly.value
  ) {
    isLoading.value = true;
    error.value = null;
    try {
      searchQuery.value = query;
      selectedDomain.value = domain;
      selectedAreaId.value = areaId;
      filterUnassignedOnly.value = unassignedOnly;

      const res = await api.searchEntities(query, domain, 150, areaId, unassignedOnly);
      entities.value = res.entities;
    } catch (e: any) {
      error.value = e.message || "Failed to load entities";
    } finally {
      isLoading.value = false;
    }
  }

  async function designateArea(entityId: string, areaId: string | null) {
    try {
      await api.designateEntityArea(entityId, areaId);
      // Update local entity
      const found = entities.value.find((e) => e.entity_id === entityId);
      if (found) {
        found.area_id = areaId;
        const matchedArea = areas.value.find((a) => a.area_id === areaId);
        found.area_name = matchedArea ? matchedArea.name : null;
      }
      await fetchAreas();
    } catch (e: any) {
      alert(e.message || "Failed to designate area");
    }
  }

  async function lookupByFriendlyName(name: string): Promise<HAEntity | null> {
    try {
      const res = await api.lookupEntityByFriendlyName(name);
      return res.entity;
    } catch {
      return null;
    }
  }

  function guessEndpointType(entity: HAEntity): EndpointType {
    const domain = entity.domain || entity.entity_id.split(".")[0];
    const devClass = entity.device_class || "";

    if (domain === "camera") return "camera";

    if (domain === "binary_sensor") {
      if (["motion", "occupancy", "presence"].includes(devClass)) {
        return "motion";
      }
      if (["door", "garage_door", "window", "opening"].includes(devClass)) {
        return "door";
      }
    }

    const friendlyLower = (entity.friendly_name || entity.name || "").toLowerCase();
    const idLower = entity.entity_id.toLowerCase();

    if (idLower.includes("motion") || friendlyLower.includes("motion")) {
      return "motion";
    }
    if (
      idLower.includes("door") ||
      friendlyLower.includes("door") ||
      idLower.includes("window") ||
      friendlyLower.includes("window")
    ) {
      return "door";
    }

    return "generic";
  }

  return {
    entities,
    areas,
    unassignedCount,
    unassignedEntities,
    isLoading,
    error,
    searchQuery,
    selectedDomain,
    selectedAreaId,
    filterUnassignedOnly,
    fetchAreas,
    fetchEntities,
    designateArea,
    lookupByFriendlyName,
    guessEndpointType,
  };
});
