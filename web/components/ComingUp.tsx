"use client";

import type { Slot } from "@/lib/types";
import { EventCountdownCard } from "./ui/EventCountdownCard";

interface Props {
  slots: Slot[];
}

export default function ComingUp({ slots }: Props) {
  if (slots.length === 0) {
    return (
      <p className="text-sm text-gray-400 py-2">
        No more shows scheduled today.
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-2.5">
      {slots.map((slot, idx) => (
        <EventCountdownCard
          key={slot.id}
          slot={slot}
          style={{ opacity: 1 - idx * 0.12 }}
        />
      ))}
    </div>
  );
}
