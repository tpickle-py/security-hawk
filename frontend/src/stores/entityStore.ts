import { defineStore } from "pinia";
import { ref, computed } from "vue";
import type { HAEntity, HAArea, EndpointType } from "@/types/plan";
import { api } from "@/services/api";
import { useLiveStore } from "@/stores/liveStore";

export const useEntityStore = defineStore("entity", () => {
  const entities = ref<HAEntity[]>([]);
  const areas = ref<HAArea[]>([]);
  const allKnownEntityIds = ref<Set<string>>(new Set());
  const ignoredEntityIds = ref<string[]>(
    JSON.parse(localStorage.getItem("sh_ignored_entities") || "[]")
  );
  const ignoredDomains = ref<string[]>(
    JSON.parse(localStorage.getItem("sh_ignored_domains") || "[]")
  );
  const unassignedCount = ref(0);
  const isLoading = ref(false);
  const error = ref<string | null>(null);

  const searchQuery = ref("");
  const selectedDomain = ref("");
  const selectedAreaId = ref("");
  const filterUnassignedOnly = ref(false);

  const unassignedEntities = computed(() => {
    return entities.value.filter((e) => !e.area_id && !isIgnored(e.entity_id));
  });

  const visibleEntities = computed(() => {
    return entities.value.filter((e) => !isIgnored(e.entity_id));
  });

  const ignoredEntities = computed(() => {
    return entities.value.filter((e) => isIgnored(e.entity_id));
  });

  const detectedDomains = computed(() => {
    const counts: Record<string, number> = {};
    for (const id of allKnownEntityIds.value) {
      const d = id.split(".")[0];
      if (d) {
        counts[d] = (counts[d] || 0) + 1;
      }
    }
    for (const ent of entities.value) {
      const d = ent.domain || ent.entity_id.split(".")[0];
      if (d && !counts[d]) {
        counts[d] = (counts[d] || 0) + 1;
      }
    }
    return Object.keys(counts)
      .map((d) => ({ domain: d, count: counts[d] }))
      .sort((a, b) => b.count - a.count);
  });

  async function fetchKnownEntityIds() {
    try {
      const res = await api.listEntityIds();
      if (res.entity_ids) {
        for (const id of res.entity_ids) {
          allKnownEntityIds.value.add(id);
        }
      }
    } catch (e: any) {
      console.warn("Could not list entity IDs:", e.message);
    }
  }

  async function loadSettingsIgnored() {
    try {
      const res = await api.getSettings();
      if (res.settings.ignored_entities && Array.isArray(res.settings.ignored_entities)) {
        ignoredEntityIds.value = res.settings.ignored_entities;
        localStorage.setItem("sh_ignored_entities", JSON.stringify(ignoredEntityIds.value));
      }
      if (res.settings.ignored_domains && Array.isArray(res.settings.ignored_domains)) {
        ignoredDomains.value = res.settings.ignored_domains;
        localStorage.setItem("sh_ignored_domains", JSON.stringify(ignoredDomains.value));
      }
    } catch {
      // Ignored
    }
  }

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

      const res = await api.searchEntities(query, domain, 300, areaId, unassignedOnly);
      entities.value = res.entities;
      for (const ent of res.entities) {
        allKnownEntityIds.value.add(ent.entity_id);
      }
    } catch (e: any) {
      error.value = e.message || "Failed to load entities";
    } finally {
      isLoading.value = false;
    }
  }

  function isKnownEntity(entityId: string | undefined | null): boolean {
    if (!entityId) return false;
    if (allKnownEntityIds.value.has(entityId)) return true;
    if (entities.value.some((e) => e.entity_id === entityId)) return true;
    try {
      const liveStore = useLiveStore();
      if (liveStore.states && liveStore.states[entityId] !== undefined) {
        allKnownEntityIds.value.add(entityId);
        return true;
      }
    } catch {
      // Live store not ready yet
    }
    return false;
  }

  function isIgnored(entityId: string | undefined | null): boolean {
    if (!entityId) return false;
    if (ignoredEntityIds.value.includes(entityId)) return true;
    const domain = entityId.split(".")[0];
    if (domain && ignoredDomains.value.includes(domain)) return true;
    return false;
  }

  function isDomainIgnored(domain: string): boolean {
    return ignoredDomains.value.includes(domain);
  }

  async function saveIgnoredState() {
    localStorage.setItem("sh_ignored_entities", JSON.stringify(ignoredEntityIds.value));
    localStorage.setItem("sh_ignored_domains", JSON.stringify(ignoredDomains.value));
    try {
      await api.saveSettings({
        ignored_entities: ignoredEntityIds.value,
        ignored_domains: ignoredDomains.value,
      });
    } catch {
      // Ignored setting sync fallback
    }
  }

  async function ignoreEntity(entityId: string) {
    if (!ignoredEntityIds.value.includes(entityId)) {
      ignoredEntityIds.value.push(entityId);
      await saveIgnoredState();
    }
  }

  async function unignoreEntity(entityId: string) {
    const idx = ignoredEntityIds.value.indexOf(entityId);
    if (idx !== -1) {
      ignoredEntityIds.value.splice(idx, 1);
      await saveIgnoredState();
    }
  }

  async function ignoreDomain(domain: string) {
    if (!ignoredDomains.value.includes(domain)) {
      ignoredDomains.value.push(domain);
      await saveIgnoredState();
    }
  }

  async function unignoreDomain(domain: string) {
    const idx = ignoredDomains.value.indexOf(domain);
    if (idx !== -1) {
      ignoredDomains.value.splice(idx, 1);
      await saveIgnoredState();
    }
  }

  async function toggleIgnoreDomain(domain: string) {
    const idx = ignoredDomains.value.indexOf(domain);
    if (idx === -1) {
      ignoredDomains.value.push(domain);
    } else {
      ignoredDomains.value.splice(idx, 1);
    }
    await saveIgnoredState();
  }

  async function ignoreMultipleDomains(domainsToIgnore: string[]) {
    let changed = false;
    for (const d of domainsToIgnore) {
      if (!ignoredDomains.value.includes(d)) {
        ignoredDomains.value.push(d);
        changed = true;
      }
    }
    if (changed) {
      await saveIgnoredState();
    }
  }

  async function unignoreAllDomains() {
    if (ignoredDomains.value.length > 0) {
      ignoredDomains.value = [];
      await saveIgnoredState();
    }
  }

  async function unignoreAll() {
    ignoredEntityIds.value = [];
    ignoredDomains.value = [];
    await saveIgnoredState();
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
    const devClass = (entity.device_class || "").toLowerCase();
    const friendlyLower = (entity.friendly_name || entity.name || "").toLowerCase();
    const idLower = entity.entity_id.toLowerCase();

    if (domain === "camera") return "camera";

    if (devClass === "window" || idLower.includes("window") || friendlyLower.includes("window")) {
      return "window";
    }

    if (
      devClass === "door" ||
      devClass === "garage_door" ||
      idLower.includes("door") ||
      friendlyLower.includes("door") ||
      idLower.includes("garage")
    ) {
      return "door";
    }

    if (
      ["motion", "occupancy", "presence"].includes(devClass) ||
      idLower.includes("motion") ||
      friendlyLower.includes("motion") ||
      friendlyLower.includes("occupancy")
    ) {
      return "motion";
    }

    // Common Zigbee contact sensors (e.g. Sonoff SNZB-04, Aqara MCCGQ)
    if (
      devClass === "opening" ||
      devClass === "contact" ||
      idLower.includes("snzb04") ||
      idLower.includes("snzb-04") ||
      idLower.includes("contact")
    ) {
      return "door";
    }

    return "generic";
  }

  return {
    entities,
    areas,
    allKnownEntityIds,
    ignoredEntityIds,
    ignoredDomains,
    detectedDomains,
    unassignedCount,
    unassignedEntities,
    visibleEntities,
    ignoredEntities,
    isLoading,
    error,
    searchQuery,
    selectedDomain,
    selectedAreaId,
    filterUnassignedOnly,
    fetchAreas,
    fetchEntities,
    fetchKnownEntityIds,
    loadSettingsIgnored,
    isKnownEntity,
    isIgnored,
    isDomainIgnored,
    ignoreEntity,
    unignoreEntity,
    ignoreDomain,
    unignoreDomain,
    toggleIgnoreDomain,
    ignoreMultipleDomains,
    unignoreAllDomains,
    unignoreAll,
    designateArea,
    lookupByFriendlyName,
    guessEndpointType,
  };
});
