"use client";

import { CheckCircle2, Radio, ScrollText, RotateCcw } from "lucide-react";
import type { Slot } from "@/lib/types";
import { parseSlotStart, formatDuration } from "@/lib/schedule";
import { getTheme } from "@/lib/themes";
import { AlertBadge } from "./ui/AlertBadge";

interface Props {
  programme: Slot[];
  currentSlotId: string | null;
  pastSlotIds: Set<string>;
  replaySlotId: string | null;
  now: Date;
  onReplay: (slot: Slot) => void;
  onShowScript: (slot: Slot) => void;
}

export default function Schedule({
  programme,
  currentSlotId,
  pastSlotIds,
  replaySlotId,
  now,
  onReplay,
  onShowScript,
}: Props) {
  return (
    <div className="flex flex-col">
      {programme.map((slot, idx) => {
        const isPast    = pastSlotIds.has(slot.id);
        const isCurrent = slot.id === currentSlotId;
        const isReplay  = slot.id === replaySlotId;
        const isLast    = idx === programme.length - 1;
        const t         = getTheme(slot.thematique);

        const start = isCurrent ? parseSlotStart(slot, now) : null;
        const elapsedMs = start ? now.getTime() - start.getTime() : 0;
        const pct = isCurrent
          ? Math.min(100, Math.max(0, (elapsedMs / (slot.duration_sec * 1000)) * 100))
          : isPast ? 100 : 0;
        const elapsedSec = isCurrent ? Math.floor(elapsedMs / 1000) : isPast ? slot.duration_sec : 0;
        const remainingSec = Math.max(0, slot.duration_sec - elapsedSec);

        return (
          <div key={slot.id} className="flex gap-3">
            <div className="flex flex-col items-center shrink-0 w-5">
              <div className={`mt-4 w-3 h-3 rounded-full shrink-0 flex items-center justify-center
                ${isCurrent
                  ? `${t.dot} ring-4 ring-orange-100 shadow-sm`
                  : isPast
                  ? "bg-gray-200"
                  : "bg-white border-2 border-gray-200"}`
              }>
                {isCurrent && <span className="w-1.5 h-1.5 rounded-full bg-white" />}
              </div>
              {!isLast && (
                <div className={`flex-1 w-px mt-1 ${isPast ? "bg-gray-200" : "bg-gray-100"}`} />
              )}
            </div>

            <div
              className={`flex-1 flex flex-col gap-1.5 py-2.5 px-3 rounded-xl mb-1 transition-all duration-200 cursor-pointer
                ${isCurrent  ? "bg-orange-50 border-2 border-orange-300 shadow-sm" : ""}
                ${isReplay   ? "bg-amber-50 border-2 border-amber-300 shadow-sm" : ""}
                ${!isCurrent && !isReplay ? "hover:bg-gray-50 hover:border-gray-300 border-2 border-transparent" : ""}`}
            >
              <div className="flex items-center gap-3">
                <div className="w-4 shrink-0">
                  {isPast && <CheckCircle2 className="w-4 h-4 text-gray-300" />}
                  {isCurrent && <Radio className="w-4 h-4 text-orange-500 animate-pulse" />}
                </div>

                <span className="text-xs font-mono font-semibold text-gray-400 tabular-nums w-11 shrink-0">
                  {slot.start_time}
                </span>

                <div className="flex-1 min-w-0">
                  <p className={`text-sm font-semibold capitalize truncate ${
                    isPast    ? "text-gray-300" :
                    isCurrent ? "text-gray-900" :
                                "text-gray-700"
                  }`}>
                    {slot.thematique}
                  </p>
                  <p className="text-xs text-gray-400 truncate mt-0.5 hidden sm:block">
                    {slot.noms.join(" · ")}
                  </p>
                </div>

                {isCurrent && (
                  <AlertBadge color="red" label="On Air" pulse className="shrink-0 hidden sm:inline-flex" />
                )}
                {isReplay && (
                  <AlertBadge color="amber" label="Replay" className="shrink-0 hidden sm:inline-flex" />
                )}

                <div className="flex items-center gap-1.5 shrink-0">
                  {slot.script && (
                    <button
                      onClick={() => onShowScript(slot)}
                      className="flex items-center gap-1 text-[11px] font-semibold text-gray-500 hover:text-gray-900 border-2 border-gray-300 hover:border-gray-700 bg-white hover:bg-gray-50 rounded-lg px-2.5 py-1.5 transition-all duration-150 cursor-pointer active:scale-95"
                    >
                      <ScrollText className="w-3 h-3" />
                      <span className="hidden sm:inline">script</span>
                    </button>
                  )}
                  {isPast && slot.audio_path && (
                    <button
                      onClick={() => onReplay(slot)}
                      className="flex items-center gap-1 text-[11px] font-semibold text-gray-500 hover:text-gray-900 border-2 border-gray-300 hover:border-gray-700 bg-white hover:bg-gray-50 rounded-lg px-2.5 py-1.5 transition-all duration-150 cursor-pointer active:scale-95"
                    >
                      <RotateCcw className="w-3 h-3" />
                      <span className="hidden sm:inline">replay</span>
                    </button>
                  )}
                </div>
              </div>

              {(isCurrent || isPast) && (
                <div className="flex items-center gap-2 pl-7">
                  <div className="flex-1 h-1.5 bg-gray-200 rounded-full overflow-hidden border border-gray-300">
                    <div
                      className={`h-full rounded-full transition-all duration-1000 ${t.bar}`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <span className="text-[10px] font-mono tabular-nums text-gray-400 shrink-0 w-16 text-right">
                    {isCurrent
                      ? `−${formatDuration(remainingSec)}`
                      : formatDuration(slot.duration_sec)}
                  </span>
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
