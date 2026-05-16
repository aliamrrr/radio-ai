"use client";

import { Mic2, ScrollText, Clock } from "lucide-react";
import type { Slot } from "@/lib/types";
import { getTheme } from "@/lib/themes";
import { FilterBadgeAvatar } from "./ui/FilterBadgeAvatar";

interface Props {
  slot: Slot | null;
  isLive: boolean;
  nextSlotTime: string | null;
  onShowScript?: (slot: Slot) => void;
}

export default function NowOnAir({ slot, isLive, nextSlotTime, onShowScript }: Props) {
  if (!slot) {
    return (
      <div className="flex flex-col gap-3">
        <p className="text-2xl font-bold text-gray-400">Off air</p>
        {nextSlotTime && (
          <div className="flex items-center gap-2 text-gray-400">
            <Clock className="w-4 h-4" />
            <span className="text-sm">
              Next show at{" "}
              <span className="font-semibold text-gray-700">{nextSlotTime}</span>
            </span>
          </div>
        )}
      </div>
    );
  }

  const t = getTheme(slot.thematique);

  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center gap-2 flex-wrap">
        <span className={`inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-1 rounded-full border-2 ${t.bg} ${t.text} ${t.border}`}>
          <span className={`w-1.5 h-1.5 rounded-full ${t.dot}`} />
          {slot.thematique}
        </span>
        <span className="text-[11px] font-mono text-gray-500 tabular-nums bg-gray-100 px-2 py-1 rounded-full border-2 border-gray-300">
          {slot.start_time}
        </span>
      </div>

      {slot.sujet && (
        <h2 className="font-display text-base sm:text-lg lg:text-xl tracking-tight text-gray-900 leading-[1.15] text-balance">
          {slot.sujet}
        </h2>
      )}

      <div className="flex items-center gap-2 flex-wrap">
        {slot.noms.map((name, i) => (
          <FilterBadgeAvatar key={name} name={name} colorIndex={i} />
        ))}
        <span className="text-gray-300">·</span>
        <div className="flex items-center gap-1 text-gray-400">
          <Mic2 className="w-3 h-3" />
          <span className="text-[11px] capitalize text-gray-500">{slot.type_script}</span>
        </div>
      </div>

      {onShowScript && slot.script && (
        <button
          onClick={() => onShowScript(slot)}
          className="self-start inline-flex items-center gap-1.5 text-[11px] font-semibold text-gray-600 hover:text-gray-900 border-2 border-gray-300 hover:border-gray-700 bg-white hover:bg-gray-50 rounded-lg px-3 py-1.5 transition-all duration-200 shadow-sm cursor-pointer active:scale-95"
        >
          <ScrollText className="w-3 h-3" />
          View script
        </button>
      )}
    </div>
  );
}
