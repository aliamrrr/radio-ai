"use client";

import { X, Mic2 } from "lucide-react";
import type { Slot } from "@/lib/types";

interface Props {
  slot: Slot;
  onClose: () => void;
}

const SPEAKER_COLORS = [
  "text-orange-700 border-orange-400 bg-orange-100",
  "text-violet-700 border-violet-400 bg-violet-100",
  "text-blue-700   border-blue-400   bg-blue-100",
  "text-emerald-700 border-emerald-400 bg-emerald-100",
];

function ScriptBody({ script, type, noms }: { script: string; type: string; noms: string[] }) {
  const lines = script.split("\n").filter(Boolean);
  const speakerColorMap = new Map<string, number>();
  noms.forEach((n, i) => speakerColorMap.set(n, i % SPEAKER_COLORS.length));

  if (type === "dialogue" || type === "debate") {
    return (
      <div className="flex flex-col gap-6">
        {lines.map((line, i) => {
          const match = line.match(/^\[(.+?)\]\s*(.*)/);
          if (match) {
            const speaker  = match[1].trim();
            const text     = match[2].trim();
            const colorIdx = speakerColorMap.get(speaker) ?? i % SPEAKER_COLORS.length;
            const colorCls = SPEAKER_COLORS[colorIdx];
            return (
              <div key={i} className="flex gap-4">
                <span className={`text-[10px] font-bold uppercase tracking-wider px-2.5 py-1 rounded-lg border-2 shrink-0 h-fit mt-1 ${colorCls}`}>
                  {speaker}
                </span>
                <p className="text-base text-gray-700 leading-relaxed flex-1">{text}</p>
              </div>
            );
          }
          return <p key={i} className="text-base text-gray-700 leading-relaxed">{line}</p>;
        })}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      {lines.map((line, i) => (
        <p key={i} className="text-base text-gray-700 leading-relaxed">{line}</p>
      ))}
    </div>
  );
}

export default function ScriptModal({ slot, onClose }: Props) {
  return (
    <div
      className="fixed inset-0 z-50 bg-black/50 backdrop-blur-md flex items-end sm:items-center justify-center p-0 sm:p-6"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-t-3xl sm:rounded-2xl shadow-2xl w-full sm:max-w-2xl max-h-[90vh] flex flex-col overflow-hidden slide-up border-2 border-gray-300"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Drag handle (mobile) */}
        <div className="flex justify-center pt-3 pb-1 sm:hidden">
          <div className="w-10 h-1 rounded-full bg-gray-200" />
        </div>

        {/* Header */}
        <div className="flex items-start justify-between px-6 py-5 border-b-2 border-gray-200 shrink-0">
          <div className="min-w-0 flex-1 pr-4">
            <div className="flex items-center gap-2 mb-2">
              <Mic2 className="w-3.5 h-3.5 text-gray-400" />
              <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-gray-400">
                Script · {slot.start_time}
              </p>
            </div>
            <h2 className="font-display text-xl sm:text-2xl text-gray-900 leading-tight">
              {slot.sujet ?? slot.thematique}
            </h2>
            <p className="text-sm text-gray-400 mt-1.5">
              {slot.noms.join(" & ")}
              <span className="mx-1.5 text-gray-200">·</span>
              <span className="capitalize">{slot.type_script}</span>
            </p>
          </div>
          <button
            onClick={onClose}
            className="group w-9 h-9 rounded-full bg-gray-100 hover:bg-gray-900 border-2 border-gray-300 hover:border-gray-900 flex items-center justify-center transition-all duration-200 cursor-pointer shrink-0"
          >
            <X className="w-4 h-4 text-gray-600 group-hover:text-white transition-colors" />
          </button>
        </div>

        {/* Script body */}
        <div className="overflow-y-auto px-6 py-6">
          {slot.script ? (
            <ScriptBody script={slot.script} type={slot.type_script} noms={slot.noms} />
          ) : (
            <p className="text-base text-gray-400 italic">
              Script is being generated…
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
