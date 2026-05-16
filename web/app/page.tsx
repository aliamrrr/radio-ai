"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import Image from "next/image";
import { Radio, ArrowLeft, Play } from "lucide-react";
import type { Programme, Slot } from "@/lib/types";
import { getTheme } from "@/lib/themes";
import {
  getCurrentSlot,
  getOffsetSec,
  getUpcoming,
  getPast,
  getNextSlotStart,
} from "@/lib/schedule";
import NowOnAir from "@/components/NowOnAir";
import Player from "@/components/Player";
import ComingUp from "@/components/ComingUp";
import Schedule from "@/components/Schedule";
import ScriptModal from "@/components/ScriptModal";
import { AlertBadge } from "@/components/ui/AlertBadge";

type Mode = "live" | "replay";

const MUSIC_COVER = "music/ChatGPT Image 16 mai 2026, 17_57_27.png";

function useClock() {
  const [now, setNow] = useState<Date | null>(null);
  useEffect(() => {
    setNow(new Date());
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);
  return now;
}

function formatClock(date: Date) {
  return date.toLocaleTimeString("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    timeZone: "Europe/Paris",
  });
}

function CoverPlaceholder({ thematique }: { thematique: string }) {
  const gradient = getTheme(thematique).gradient;
  return (
    <div className={`w-full h-full bg-gradient-to-br ${gradient} flex items-center justify-center`}>
      <span className="text-8xl font-black text-white/20 select-none">
        {thematique.charAt(0).toUpperCase()}
      </span>
    </div>
  );
}

export default function RadioPage() {
  const [programme, setProgramme] = useState<Programme>([]);
  const [mode, setMode] = useState<Mode>("live");
  const [replaySlot, setReplaySlot] = useState<Slot | null>(null);
  const [scriptSlot, setScriptSlot] = useState<Slot | null>(null);
  const [radioStarted, setRadioStarted] = useState(false);
  const now = useClock();

  const fetchProgramme = useCallback(async () => {
    try {
      const res = await fetch("/api/programme");
      if (res.ok) setProgramme(await res.json());
    } catch {}
  }, []);

  useEffect(() => { fetchProgramme(); }, [fetchProgramme]);
  useEffect(() => {
    const id = setInterval(fetchProgramme, 60_000);
    return () => clearInterval(id);
  }, [fetchProgramme]);

  const safeNow = now ?? new Date();
  const currentLiveSlot = getCurrentSlot(programme, safeNow);
  const offsetSec = currentLiveSlot ? getOffsetSec(currentLiveSlot, safeNow) : 0;
  const upcomingSlots = getUpcoming(programme, safeNow, 3);
  const pastSlots = getPast(programme, safeNow);
  const pastSlotIds = useMemo(() => new Set(pastSlots.map((s) => s.id)), [pastSlots]);
  const nextSlotTime = getNextSlotStart(programme, safeNow);
  const activeSlot = mode === "live" ? currentLiveSlot : replaySlot;
  const isOnAir = !!currentLiveSlot;

  const handleSlotEnded = useCallback(() => {
    // Live mode is clock-driven — let getCurrentSlot pick the next slot naturally.
    // Only auto-advance in replay mode.
    if (mode === "live") return;
    if (!activeSlot || programme.length === 0) return;
    const idx = programme.findIndex((s) => s.id === activeSlot.id);
    const next = programme[idx + 1] ?? programme[0];
    setReplaySlot(next);
  }, [mode, activeSlot, programme]);

  const ip = activeSlot?.image_path ?? (activeSlot?.type_script === "music" ? MUSIC_COVER : null);
  const coverSrc = ip
    ? (ip.startsWith("http") ? ip : `/api/media/${ip.split("/").map(encodeURIComponent).join("/")}`)
    : null;

  return (
    <div className="min-h-screen bg-[#f0f0f2]">
      {scriptSlot && (
        <ScriptModal slot={scriptSlot} onClose={() => setScriptSlot(null)} />
      )}

      <header className="sticky top-0 z-30 bg-white/90 backdrop-blur-xl border-b-2 border-gray-200 shadow-sm">
        <div className="w-full px-5 sm:px-8 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-xl bg-orange-500 flex items-center justify-center shrink-0 shadow-md shadow-orange-500/30">
              <Radio className="w-4 h-4 text-white" />
            </div>
            <div className="flex items-baseline gap-2">
              <span className="font-display tracking-tight text-gray-900 text-xl">Next Radio</span>
              <span className="text-gray-400 font-semibold text-xs uppercase tracking-widest">24/7</span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {mode === "replay" ? (
              <button
                onClick={() => { setMode("live"); setReplaySlot(null); }}
                className="flex items-center gap-1.5 text-sm font-medium text-gray-500 hover:text-gray-900 transition-colors"
              >
                <ArrowLeft className="w-4 h-4" />
                Back to live
              </button>
            ) : isOnAir ? (
              <AlertBadge color="red" label="On air" pulse />
            ) : null}
            {now && (
              <span className="text-sm font-mono text-gray-400 tabular-nums hidden sm:block">
                {formatClock(now)}
              </span>
            )}
          </div>
        </div>
      </header>

      {!radioStarted && programme.length > 0 && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-white/96 backdrop-blur-2xl">
          <button
            onClick={() => setRadioStarted(true)}
            className="flex flex-col items-center gap-8 group cursor-pointer"
          >
            <div className="relative">
              <div className="absolute inset-0 rounded-full bg-orange-400/30 scale-125 blur-xl group-hover:scale-150 transition-transform duration-500" />
              <div className="relative w-32 h-32 rounded-full bg-gradient-to-br from-orange-400 to-orange-600 flex items-center justify-center shadow-2xl shadow-orange-500/40 group-hover:scale-110 active:scale-95 transition-transform duration-300 border-4 border-orange-300">
                <Play className="w-14 h-14 text-white ml-2" />
              </div>
            </div>
            <div className="flex flex-col items-center gap-2">
              <span className="font-display text-gray-900 text-3xl tracking-tight">Start listening</span>
              <span className="text-gray-400 text-sm font-medium">Autoplay · 24/7</span>
            </div>
          </button>
        </div>
      )}

      <main className="w-full px-5 sm:px-8 py-8 flex flex-col gap-6">

        <section className="card rounded-2xl overflow-hidden fade-up">
          <div className="flex flex-col sm:flex-row">

            <div className="relative w-full h-52 sm:w-1/2 sm:h-auto sm:aspect-[11/6] shrink-0 overflow-hidden bg-gray-900">
              {coverSrc ? (
                <Image
                  src={coverSrc}
                  alt={activeSlot?.sujet ?? activeSlot?.thematique ?? ""}
                  fill
                  className="object-contain"
                  unoptimized
                />
              ) : activeSlot ? (
                <CoverPlaceholder thematique={activeSlot.thematique} />
              ) : (
                <div className="w-full h-full flex items-center justify-center bg-gray-100">
                  <Radio className="w-20 h-20 text-gray-300" />
                </div>
              )}

              <div className="absolute inset-0 bg-gradient-to-t from-black/50 via-transparent to-transparent sm:hidden" />

              {mode === "live" && currentLiveSlot && (
                <div className="absolute top-3 left-3">
                  <AlertBadge color="red" label="Live" pulse className="shadow-lg" />
                </div>
              )}
              {mode === "replay" && replaySlot && (
                <div className="absolute top-3 left-3">
                  <AlertBadge color="amber" label="Replay" className="shadow-lg" />
                </div>
              )}
            </div>

            {/* Content */}
            <div className="flex-1 flex flex-col min-w-0 p-3 sm:p-4 gap-2 justify-center overflow-y-auto bg-white">
              <NowOnAir
                slot={activeSlot}
                isLive={mode === "live"}
                nextSlotTime={nextSlotTime}
                onShowScript={(s) => setScriptSlot(s)}
              />
              <Player
                slot={activeSlot}
                seekTo={mode === "live" ? offsetSec : 0}
                isLive={mode === "live"}
                autoplay={radioStarted}
                onEnded={handleSlotEnded}
              />
            </div>
          </div>
        </section>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <section className="card rounded-2xl p-6 fade-up" style={{ animationDelay: "0.05s" }}>
            <SectionLabel>Coming up</SectionLabel>
            <ComingUp slots={upcomingSlots} />
          </section>

          <section className="lg:col-span-2 card rounded-2xl p-6 fade-up" style={{ animationDelay: "0.1s" }}>
            <SectionLabel>Today&apos;s schedule</SectionLabel>
            <Schedule
              programme={programme}
              currentSlotId={currentLiveSlot?.id ?? null}
              pastSlotIds={pastSlotIds}
              replaySlotId={replaySlot?.id ?? null}
              now={safeNow}
              onReplay={(slot) => { setReplaySlot(slot); setMode("replay"); }}
              onShowScript={(slot) => setScriptSlot(slot)}
            />
          </section>
        </div>

        <footer className="text-center text-xs text-gray-400 pb-4 pt-2">
          AI-generated content · Updated nightly at midnight
        </footer>
      </main>
    </div>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-[11px] font-bold tracking-[0.2em] uppercase text-gray-500 mb-5">
      {children}
    </p>
  );
}
