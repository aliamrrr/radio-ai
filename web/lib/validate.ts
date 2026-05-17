import type { Slot } from "./types";

const VALID_SCRIPT_TYPES = new Set([
  "presentation", "dialogue", "story", "debate",
  "analysis", "daily recap", "music",
]);

const HH_MM = /^\d{2}:\d{2}$/;
const SAFE_ID = /^[a-zA-Z0-9_\-]+$/;

function isString(v: unknown, maxLen: number): v is string {
  return typeof v === "string" && v.length <= maxLen;
}

function isValidSlot(s: unknown): s is Slot {
  if (!s || typeof s !== "object") return false;
  const o = s as Record<string, unknown>;

  return (
    isString(o.id, 50) && SAFE_ID.test(o.id) &&
    isString(o.start_time, 5) && HH_MM.test(o.start_time) &&
    typeof o.duration_sec === "number" && o.duration_sec >= 0 &&
    isString(o.thematique, 100) &&
    typeof o.nb_intervenants === "number" &&
    Array.isArray(o.noms) && o.noms.length <= 10 &&
    isString(o.langue, 10) &&
    isString(o.type_script, 50) && VALID_SCRIPT_TYPES.has(o.type_script) &&
    (o.sujet === null || isString(o.sujet, 500)) &&
    (o.script === null || isString(o.script, 50_000)) &&
    (o.image_path === null || isString(o.image_path, 2000)) &&
    // audio_path: local relative path OR full https URL (R2 in production)
    (o.audio_path === null || isString(o.audio_path, 2000))
  );
}

/** Validate and filter a raw JSON array into a typed Slot[]. */
export function validateProgramme(raw: unknown): Slot[] {
  if (!Array.isArray(raw)) return [];
  return raw.filter(isValidSlot);
}
