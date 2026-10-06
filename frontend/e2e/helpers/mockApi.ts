import type { Page } from "@playwright/test";

export interface MockDataOptions {
  planId?: string;
  planName?: string;
}

export async function setupMockApi(page: Page, options: MockDataOptions = {}) {
  // Ensure every test starts with clean local storage and default Mapping workspace
  page.on("console", msg => console.log(`[BROWSER] ${msg.text()}`));
  await page.addInitScript(() => {
    try {
      localStorage.clear();
      sessionStorage.clear();
    } catch {}
  });

  const planId = options.planId || "plan_main";
  const planName = options.planName || "HQ Security Campus";

  const defaultFloor = {
    id: "floor_1",
    name: "Ground Floor",
    shapes: [
      {
        id: "wall_1",
        type: "wall",
        geometry: {
          x1: 100,
          y1: 50,
          x2: 500,
          y2: 50,
          thickness: 8,
          openings: [
            { id: "door_1", type: "door", offset: 150, width: 40, swing: "inward" },
          ],
        },
        style: { stroke: "#94a3b8" },
      },
      {
        id: "room_1",
        type: "room",
        geometry: {
          points: [
            [100, 100],
            [500, 100],
            [500, 400],
            [100, 400],
          ],
          name: "Server Room",
        },
        style: { fill: "rgba(99, 102, 241, 0.12)", stroke: "#6366f1" },
      },
    ],
    sub_areas: [
      {
        id: "sa_1",
        name: "Living Room",
        x: 120,
        y: 120,
        width: 250,
        height: 180,
        color: "rgba(99, 102, 241, 0.08)",
      },
      {
        id: "sa_2",
        name: "Datacenter",
        x: 420,
        y: 120,
        width: 200,
        height: 180,
        color: "rgba(16, 185, 129, 0.08)",
      },
    ],
    endpoints: [
      {
        id: "ep_cam_1",
        entity_id: "camera.server_room_cam",
        type: "camera",
        label: "Server Cam",
        x: 450,
        y: 150,
        rotation: 0,
        fov_beam_angle: 90,
        fov_depth_px: 120,
      },
      {
        id: "ep_motion_1",
        entity_id: "binary_sensor.living_room_motion",
        type: "motion",
        label: "Living Room PIR",
        x: 550,
        y: 200,
        rotation: 45,
      },
      {
        id: "ep_door_1",
        entity_id: "binary_sensor.front_door_contact",
        type: "door",
        label: "Front Door Sensor",
        x: 650,
        y: 200,
        rotation: 0,
      },
    ],
  };

  const defaultPlan = {
    id: planId,
    name: planName,
    scale_pixels_per_meter: 50,
    buildings: [
      {
        id: "bld_1",
        name: "Main Campus",
        x: 0,
        y: 0,
        floors: [defaultFloor],
      },
    ],
    overview: {
      endpoints: defaultFloor.endpoints,
      sub_areas: defaultFloor.sub_areas,
    },
  };

  // Mock Plan APIs
  await page.route("**/api/plans/**", async (route) => {
    const method = route.request().method();
    if (method === "GET") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ id: defaultPlan.id, plan: defaultPlan, plans: [defaultPlan] }),
      });
    } else if (method === "PUT" || method === "POST") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ status: "saved", plan: defaultPlan }),
      });
    } else {
      await route.continue();
    }
  });

  // Mock Areas API
  await page.route("**/api/areas/**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        areas: [
          { area_id: "server_room", name: "Server Room", entity_count: 3 },
          { area_id: "living_room", name: "Living Room", entity_count: 5 },
          { area_id: "datacenter", name: "Datacenter", entity_count: 2 },
          { area_id: "garage", name: "Garage", entity_count: 1 },
        ],
        total_areas: 4,
        unassigned_entities_count: 4,
      }),
    });
  });

  // Mock Entities API
  await page.route("**/api/entities/**", async (route) => {
    const url = route.request().url();
    const method = route.request().method();

    if (method === "POST" && url.includes("/area/")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ status: "designated" }),
      });
      return;
    }

    if (url.includes("/ids/")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          entity_ids: [
            "camera.server_room_cam",
            "camera.datacenter_cam",
            "camera.garage_cam",
            "binary_sensor.living_room_motion",
            "binary_sensor.front_door_contact",
            "binary_sensor.garage_motion",
          ],
        }),
      });
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        entities: [
          {
            entity_id: "camera.living_room_cam",
            friendly_name: "Living Room Wyze Cam",
            domain: "camera",
            area_id: null,
          },
          {
            entity_id: "camera.datacenter_cam",
            friendly_name: "Datacenter Server Cam",
            domain: "camera",
            area_id: null,
          },
          {
            entity_id: "binary_sensor.living_room_motion",
            friendly_name: "Living Room PIR Motion",
            domain: "binary_sensor",
            device_class: "motion",
            area_id: null,
          },
        ],
      }),
    });
  });

  // Mock Rules API
  await page.route("**/api/rules/**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        rules: [
          {
            id: "rule_1",
            name: "Datacenter Intrusion Alarm",
            output_entity_id: "binary_sensor.security_hawk_datacenter_alarm",
            conditions: [{ entity_id: "binary_sensor.living_room_motion", state: "on" }],
            logic: "ALL",
            time_window_seconds: 30,
            actions: [{ type: "ha_service", service: "light.turn_on" }],
          },
          {
            id: "rule_server_intrusion",
            name: "Server Room Intrusion Alarm",
            output_entity_id: "binary_sensor.security_hawk_server_intrusion",
            conditions: [{ entity_id: "binary_sensor.living_room_motion", state: "on" }],
            logic: "ALL",
            time_window_seconds: 30,
            actions: [{ type: "ha_service", service: "light.turn_on" }],
          },
        ],
      }),
    });
  });

  // Mock Settings API
  await page.route("**/api/settings/**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        settings: {
          ignored_entities: [],
          ignored_domains: [],
          mcp_access_level: "full_access",
        },
      }),
    });
  });

  // Mock MCP Security Audit API
  await page.route("**/api/mcp/execute", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        plan_name: "HQ Security Campus",
        status: "action_recommended",
        stats: {
          rooms_count: 1,
          sub_areas_count: 2,
          walls_count: 1,
          door_cutouts_count: 1,
          total_sensors_placed: 3,
        },
        recommendations: [
          "Add contact sensor or camera coverage to rear patio doorway",
          "Living Room motion sensor angle has 10m dead zone",
        ],
      }),
    });
  });
}
