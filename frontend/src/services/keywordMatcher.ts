/**
 * Smart Keyword Library & Area Matching Engine for Security Hawk.
 *
 * Automatically correlates Home Assistant entities with target rooms/areas
 * based on friendly names, entity IDs, common architectural abbreviations,
 * and semantic synonym dictionaries.
 */

import type { HAArea, HAEntity } from "../types/plan";

export interface SmartMatchResult {
  entity: HAEntity;
  matchedArea: HAArea;
  confidence: "high" | "medium";
  score: number; // 0.0 - 1.0
  reason: string;
}

/**
 * Keyword taxonomy mapping standard room concepts to tokens, abbreviations, and synonyms.
 */
export const ROOM_KEYWORD_TAXONOMY: Record<string, string[]> = {
  living_room: [
    "living",
    "liv",
    "lr",
    "family",
    "family_room",
    "sitting",
    "lounge",
    "great_room",
    "tv_room",
    "salon",
    "parlor",
  ],
  kitchen: [
    "kitchen",
    "kit",
    "pantry",
    "nook",
    "breakfast",
    "scullery",
    "galley",
    "prep",
    "cook",
  ],
  dining_room: [
    "dining",
    "din",
    "dr",
    "dining_room",
    "eating",
    "banquet",
  ],
  master_bedroom: [
    "master",
    "mbr",
    "primary",
    "main_bed",
    "owner",
    "suite",
    "master_bed",
    "primary_bed",
    "master_bedroom",
    "primary_bedroom",
  ],
  bedroom: [
    "bedroom",
    "bed",
    "br",
    "guest",
    "guest_room",
    "nursery",
    "kids",
    "boy",
    "girl",
    "bunk",
    "spare",
    "sleep",
  ],
  bathroom: [
    "bathroom",
    "bath",
    "ba",
    "wc",
    "powder",
    "powder_room",
    "ensuite",
    "half_bath",
    "washroom",
    "toilet",
    "restroom",
    "lavatory",
  ],
  garage: [
    "garage",
    "gar",
    "workshop",
    "shop",
    "carport",
    "shed",
    "barn",
    "storage_room",
  ],
  entryway: [
    "entry",
    "entryway",
    "foyer",
    "vestibule",
    "hall",
    "hallway",
    "corridor",
    "front_door",
    "porch",
    "front_porch",
    "mudroom",
    "mud_room",
  ],
  office: [
    "office",
    "study",
    "den",
    "studio",
    "library",
    "desk",
    "workstation",
    "craft",
    "sewing",
  ],
  basement: [
    "basement",
    "base",
    "cellar",
    "crawl",
    "crawlspace",
    "lower_level",
    "underground",
  ],
  attic: [
    "attic",
    "loft",
    "garret",
  ],
  laundry: [
    "laundry",
    "utility",
    "washer",
    "dryer",
    "utility_room",
    "laundry_room",
  ],
  exterior: [
    "exterior",
    "outside",
    "yard",
    "backyard",
    "front_yard",
    "garden",
    "patio",
    "deck",
    "balcony",
    "terrace",
    "pool",
    "driveway",
    "courtyard",
    "sidewalk",
    "walkway",
  ],
};

/**
 * Normalizes text: lowercase, removes punctuation, splits snake_case/kebab-case.
 */
export function tokenizeText(input: string): string[] {
  if (!input) return [];
  return input
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim()
    .split(/\s+/)
    .filter((t) => t.length > 0);
}

/**
 * Strips Home Assistant domain (e.g. "binary_sensor." or "camera.") from entity ID.
 */
export function stripEntityDomain(entityId: string): string {
  const parts = entityId.split(".");
  return parts.length > 1 ? parts.slice(1).join(".") : entityId;
}

/**
 * Determines whether a taxonomy key or token aligns with an area name.
 */
function areaMatchesTaxonomyCategory(areaName: string, category: string): boolean {
  const areaTokens = tokenizeText(areaName);
  const synonyms = ROOM_KEYWORD_TAXONOMY[category] || [];
  return areaTokens.some((at) => synonyms.includes(at) || at === category.replace("_", ""));
}

/**
 * Attempts to match a single entity to the most appropriate area.
 */
export function matchEntityToArea(
  entity: HAEntity,
  areas: HAArea[]
): SmartMatchResult | null {
  if (!areas.length) return null;

  const friendlyName = entity.friendly_name || entity.name || "";
  const entityBaseId = stripEntityDomain(entity.entity_id);

  const friendlyTokens = tokenizeText(friendlyName);
  const idTokens = tokenizeText(entityBaseId);
  const combinedTokens = Array.from(new Set([...friendlyTokens, ...idTokens]));

  let bestMatch: SmartMatchResult | null = null;
  let highestScore = 0;

  for (const area of areas) {
    const areaTokens = tokenizeText(area.name);
    const areaFullNameNorm = area.name.toLowerCase().trim();
    const friendlyLower = friendlyName.toLowerCase().trim();
    const idLower = entityBaseId.toLowerCase();

    // 1. Direct Substring Match (Highest Confidence)
    // Example: Area "Living Room", Entity "Living Room Motion Sensor"
    if (areaFullNameNorm.length > 2 && (friendlyLower.includes(areaFullNameNorm) || idLower.includes(areaFullNameNorm))) {
      const score = 0.98;
      if (score > highestScore) {
        highestScore = score;
        bestMatch = {
          entity,
          matchedArea: area,
          confidence: "high",
          score,
          reason: `Entity explicitly contains area name "${area.name}"`,
        };
      }
      continue;
    }

    // 2. Token Intersection Match
    // Example: Area "Master Bedroom", Entity "sensor.master_bed_window"
    const commonTokens = areaTokens.filter((t) => combinedTokens.includes(t));
    if (commonTokens.length === areaTokens.length && areaTokens.length > 0) {
      const score = 0.92;
      if (score > highestScore) {
        highestScore = score;
        bestMatch = {
          entity,
          matchedArea: area,
          confidence: "high",
          score,
          reason: `Matches all tokens of area "${area.name}" (${commonTokens.join(", ")})`,
        };
      }
      continue;
    }

    // 3. Keyword Taxonomy / Alias Match
    // Example: Entity "binary_sensor.mbr_motion", Area "Master Bedroom" -> "mbr" matches taxonomy
    for (const [category, synonyms] of Object.entries(ROOM_KEYWORD_TAXONOMY)) {
      if (areaMatchesTaxonomyCategory(area.name, category)) {
        const matchedSynonym = synonyms.find((syn) => combinedTokens.includes(syn));
        if (matchedSynonym) {
          const isHigh = matchedSynonym.length >= 3 || ["lr", "br", "wc", "ba"].includes(matchedSynonym);
          const score = isHigh ? 0.88 : 0.76;
          if (score > highestScore) {
            highestScore = score;
            bestMatch = {
              entity,
              matchedArea: area,
              confidence: isHigh ? "high" : "medium",
              score,
              reason: `Matched architectural abbreviation "${matchedSynonym}" for ${area.name}`,
            };
          }
        }
      }
    }

    // 4. Area Aliases from Home Assistant
    if (area.aliases && Array.isArray(area.aliases)) {
      for (const alias of area.aliases) {
        const aliasLower = alias.toLowerCase().trim();
        if (aliasLower && (friendlyLower.includes(aliasLower) || idLower.includes(aliasLower))) {
          const score = 0.94;
          if (score > highestScore) {
            highestScore = score;
            bestMatch = {
              entity,
              matchedArea: area,
              confidence: "high",
              score,
              reason: `Matched configured area alias "${alias}"`,
            };
          }
        }
      }
    }
  }

  // Only return if match meets minimum confidence threshold
  if (bestMatch && bestMatch.score >= 0.70) {
    return bestMatch;
  }

  return null;
}

/**
 * Finds all smart matches across a set of unassigned entities.
 */
export function findSmartMatches(
  entities: HAEntity[],
  areas: HAArea[]
): SmartMatchResult[] {
  const matches: SmartMatchResult[] = [];
  for (const ent of entities) {
    if (!ent.area_id) {
      const match = matchEntityToArea(ent, areas);
      if (match) {
        matches.push(match);
      }
    }
  }
  return matches;
}
