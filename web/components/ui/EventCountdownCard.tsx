"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { parseSlotStart } from "@/lib/schedule";
import { getTheme } from "@/lib/themes";
import type { Slot } from "@/lib/types";

function buildCountdown(diffMs: number) {
  if (diffMs <= 0) return null;
  const total = Math.floor(diffMs / 1000);
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  return {
    h: String(h).padStart(2, "0"),
    m: String(m).padStart(2, "0"),
    s: String(s).padStart(2, "0"),
  };
}

function AnimatedDigit({ value, color }: { value: string; color: string }) {
  return (
    <div className="relative w-5 h-7 overflow-hidden">
      <AnimatePresence mode="popLayout" initial={false}>
        <motion.span
          key={value}
          initial={{ y: -18, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: 18, opacity: 0 }}
          transition={{ duration: 0.16, ease: "easeInOut" }}
          className={`absolute inset-0 flex items-center justify-center text-base font-black tabular-nums ${color}`}
        >
          {value}
        </motion.span>
      </AnimatePresence>
    </div>
  );
}

interface EventCountdownCardProps {
  slot: Slot;
  style?: React.CSSProperties;
}

export function EventCountdownCard({ slot, style }: EventCountdownCardProps) {
  const [countdown, setCountdown] = useState<{ h: string; m: string; s: string } | null>(null);

  useEffect(() => {
    const target = parseSlotStart(slot, new Date());
    const tick = () => setCountdown(buildCountdown(target.getTime() - Date.now()));
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [slot.start_time]);

  const t = getTheme(slot.thematique);

  return (
    <div
      className={`flex items-stretch gap-3 rounded-xl border-2 p-3.5 transition-all ${t.bg} ${t.border}`}
      style={style}
    >
      <div className={`w-1 self-stretch rounded-full shrink-0 ${t.dot}`} />

      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between gap-2 mb-0.5">
          <span className={`text-xs font-bold uppercase tracking-wide capitalize truncate ${t.text}`}>
            {slot.thematique}
          </span>
          <span className="text-xs font-mono text-gray-400 tabular-nums shrink-0">{slot.start_time}</span>
        </div>

        <p className="text-xs text-gray-400 truncate mb-2.5">{slot.noms.join(" · ")}</p>

        {countdown ? (
          <div className="flex items-center gap-0.5">
            <AnimatedDigit value={countdown.h[0]} color={t.digits} />
            <AnimatedDigit value={countdown.h[1]} color={t.digits} />
            <span className="text-base font-black text-gray-300 mx-0.5 leading-7">:</span>
            <AnimatedDigit value={countdown.m[0]} color={t.digits} />
            <AnimatedDigit value={countdown.m[1]} color={t.digits} />
            <span className="text-base font-black text-gray-300 mx-0.5 leading-7">:</span>
            <AnimatedDigit value={countdown.s[0]} color={t.digits} />
            <AnimatedDigit value={countdown.s[1]} color={t.digits} />
            <span className="ml-2 text-[10px] text-gray-400 font-medium self-end pb-0.5">left</span>
          </div>
        ) : (
          <span className="text-xs text-gray-400 italic">Starting soon…</span>
        )}
      </div>
    </div>
  );
}
