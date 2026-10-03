import type { HAArea, HAEntity, Site } from "@/types/plan";

declare global {
  interface Window {
    __INGRESS_PATH__?: string;
  }
}

export function getBasePath(): string {
  // If injected by Django backend
  const injected = window.__INGRESS_PATH__;
  if (injected) {
    return injected.endsWith("/") ? injected.slice(0, -1) : injected;
  }
  // Otherwise check if path contains ingress
  const match = window.location.pathname.match(/^(.*\/api\/hassio_ingress\/[^/]+)/);
  if (match) {
    return match[1];
  }
  return "";
}

const BASE_URL = getBasePath();

export const api = {
  async getHealth(): Promise<{ status: string; version: string }> {
    const res = await fetch(`${BASE_URL}/api/health/`);
    if (!res.ok) throw new Error("Health check failed");
    return res.json();
  },

  async listPlans(): Promise<{ plans: Array<{ id: string; name: string; modified: number; size: number }> }> {
    const res = await fetch(`${BASE_URL}/api/plans/`);
    if (!res.ok) throw new Error("Failed to list plans");
    return res.json();
  },

  async createPlan(name: string): Promise<{ id: string; plan: Site }> {
    const res = await fetch(`${BASE_URL}/api/plans/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    });
    if (!res.ok) throw new Error("Failed to create plan");
    return res.json();
  },

  async getPlan(planId: string): Promise<{ id: string; plan: Site }> {
    const res = await fetch(`${BASE_URL}/api/plans/${planId}/`);
    if (!res.ok) throw new Error(`Failed to load plan: ${res.statusText}`);
    return res.json();
  },

  async updatePlan(planId: string, plan: Site): Promise<{ status: string }> {
    const res = await fetch(`${BASE_URL}/api/plans/${planId}/`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(plan),
    });
    if (!res.ok) throw new Error("Failed to save plan");
    return res.json();
  },

  async deletePlan(planId: string): Promise<{ status: string }> {
    const res = await fetch(`${BASE_URL}/api/plans/${planId}/`, {
      method: "DELETE",
    });
    if (!res.ok) throw new Error("Failed to delete plan");
    return res.json();
  },

  async uploadAsset(planId: string, file: File): Promise<{
    asset_id: string;
    filename: string;
    original_name: string;
    url: string;
    size: number;
  }> {
    const formData = new FormData();
    formData.append("file", file);

    const res = await fetch(`${BASE_URL}/api/plans/${planId}/assets/`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ error: "Asset upload failed" }));
      throw new Error(err.error || "Asset upload failed");
    }
    return res.json();
  },

  async listVersions(planId: string): Promise<{
    versions: Array<{ filename: string; modified: number; size: number }>;
  }> {
    const res = await fetch(`${BASE_URL}/api/plans/${planId}/versions/`);
    if (!res.ok) throw new Error("Failed to list versions");
    return res.json();
  },

  async restoreVersion(planId: string, version: string): Promise<{ status: string; plan: Site }> {
    const res = await fetch(`${BASE_URL}/api/plans/${planId}/restore/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ version }),
    });
    if (!res.ok) throw new Error("Failed to restore version");
    return res.json();
  },

  getExportUrl(planId: string): string {
    return `${BASE_URL}/api/plans/${planId}/export/`;
  },

  async importPlan(
    file: File,
    planId?: string
  ): Promise<{ status: string; plan_id: string; plan: Site; migrated: boolean }> {
    const formData = new FormData();
    formData.append("file", file);
    const url = planId ? `${BASE_URL}/api/plans/${planId}/import/` : `${BASE_URL}/api/plans/import/`;
    const res = await fetch(url, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ error: "Import failed" }));
      throw new Error(err.error || "Import failed");
    }
    return res.json();
  },

  async searchEntities(
    query = "",
    domain = "",
    limit = 50,
    areaId = "",
    unassignedOnly = false
  ): Promise<{ entities: HAEntity[] }> {
    const params = new URLSearchParams();
    if (query) params.set("q", query);
    if (domain) params.set("domain", domain);
    if (limit) params.set("limit", String(limit));
    if (areaId) params.set("area_id", areaId);
    if (unassignedOnly) params.set("unassigned_area", "true");

    const res = await fetch(`${BASE_URL}/api/entities/?${params.toString()}`);
    if (!res.ok) throw new Error("Failed to search entities");
    return res.json();
  },

  async lookupEntityByFriendlyName(name: string): Promise<{ entity: HAEntity }> {
    const params = new URLSearchParams({ name });
    const res = await fetch(`${BASE_URL}/api/entities/lookup/?${params.toString()}`);
    if (!res.ok) throw new Error("Failed to lookup entity by friendly name");
    return res.json();
  },

  async listAreas(): Promise<{ areas: HAArea[]; total_areas: number; unassigned_entities_count: number }> {
    const res = await fetch(`${BASE_URL}/api/areas/`);
    if (!res.ok) throw new Error("Failed to list areas");
    return res.json();
  },

  async designateEntityArea(entityId: string, areaId: string | null): Promise<{ status: string }> {
    const res = await fetch(`${BASE_URL}/api/entities/${entityId}/area/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ area_id: areaId }),
    });
    if (!res.ok) throw new Error("Failed to designate entity area");
    return res.json();
  },

  async getEntity(entityId: string): Promise<{ entity: HAEntity; state: Record<string, unknown> | null }> {
    const res = await fetch(`${BASE_URL}/api/entities/${entityId}/`);
    if (!res.ok) throw new Error("Failed to get entity");
    return res.json();
  },

  getCameraSnapshotUrl(entityId: string): string {
    return `${BASE_URL}/api/camera/${entityId}/?t=${Date.now()}`;
  },

  resolveAssetUrl(url: string): string {
    if (url.startsWith("http://") || url.startsWith("https://") || url.startsWith("data:")) {
      return url;
    }
    const cleanUrl = url.startsWith("/") ? url : `/${url}`;
    return `${BASE_URL}${cleanUrl}`;
  },

  getWebSocketUrl(planId: string): string {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    const pathPrefix = BASE_URL;
    return `${protocol}//${host}${pathPrefix}/ws/live/${planId}/`;
  },
};
