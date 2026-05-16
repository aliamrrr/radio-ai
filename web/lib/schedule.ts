import { toZonedTime } from "date-fns-tz";
import type { Programme, Slot } from "./types";

const TIMEZONE = "Europe/Paris";

export function parseSlotStart(slot: Slot, referenceDate: Date): Date {
  const zoned = toZonedTime(referenceDate, TIMEZONE);
  const [hours, minutes] = slot.start_time.split(":").map(Number);
  const slotDate = new Date(zoned);
  slotDate.setHours(hours, minutes, 0, 0);
  return slotDate;
}

function getSlotEnd(slot: Slot, start: Date): Date {
  return new Date(start.getTime() + slot.duration_sec * 1000);
}

export function getCurrentSlot(programme: Programme, now: Date): Slot | null {
  for (const slot of programme) {
    const start = parseSlotStart(slot, now);
    const end = getSlotEnd(slot, start);
    if (now >= start && now < end) {
      return slot;
    }
  }
  return null;
}

export function getOffsetSec(slot: Slot, now: Date): number {
  const start = parseSlotStart(slot, now);
  return Math.max(0, Math.floor((now.getTime() - start.getTime()) / 1000));
}

export function getUpcoming(programme: Programme, now: Date, n = 3): Slot[] {
  const upcoming: Slot[] = [];
  for (const slot of programme) {
    const start = parseSlotStart(slot, now);
    if (start > now) {
      upcoming.push(slot);
      if (upcoming.length >= n) break;
    }
  }
  return upcoming;
}

export function getPast(programme: Programme, now: Date): Slot[] {
  return programme.filter((slot) => {
    const start = parseSlotStart(slot, now);
    const end = getSlotEnd(slot, start);
    return end <= now;
  });
}

export function getNextSlotStart(programme: Programme, now: Date): string | null {
  for (const slot of programme) {
    const start = parseSlotStart(slot, now);
    if (start > now) {
      return slot.start_time;
    }
  }
  return null;
}

export function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}
