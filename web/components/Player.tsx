"use client";

import { useEffect, useRef, useState } from "react";
import { Play, Pause, Volume2 } from "lucide-react";
import { formatDuration } from "@/lib/schedule";
import type { Slot } from "@/lib/types";

interface Props {
  slot: Slot | null;
  seekTo?: number;
  isLive: boolean;
  autoplay?: boolean;
  onEnded?: () => void;
}

function LiveProgress({ slot, seekTo }: { slot: Slot; seekTo: number }) {
  const [elapsed, setElapsed] = useState(seekTo);
  useEffect(() => {
    setElapsed(seekTo);
    const id = setInterval(() => setElapsed(s => Math.min(s + 1, slot.duration_sec)), 1000);
    return () => clearInterval(id);
  }, [seekTo, slot.duration_sec]);
  const pct = Math.min(100, (elapsed / slot.duration_sec) * 100);
  const remaining = Math.max(0, slot.duration_sec - elapsed);
  return (
    <div className="flex flex-col gap-1.5">
      <div className="relative h-2 bg-gray-200 rounded-full overflow-hidden border border-gray-300">
        <div
          className="absolute left-0 top-0 h-full bg-gradient-to-r from-orange-500 to-orange-400 rounded-full transition-all duration-1000"
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="flex justify-between text-[11px] font-mono text-gray-400 tabular-nums">
        <span>{formatDuration(elapsed)}</span>
        <span className="text-red-500 font-bold text-[10px] tracking-wider animate-pulse">LIVE</span>
        <span>−{formatDuration(remaining)}</span>
      </div>
    </div>
  );
}

const BAR_HEIGHTS = [30, 55, 70, 45, 85, 60, 90, 40, 75, 50, 80, 35, 65, 55, 45, 70, 90, 60, 40, 75];
const BAR_DELAYS  = [0, 0.1, 0.2, 0.15, 0.05, 0.25, 0.3, 0.08, 0.18, 0.12, 0.22, 0.35, 0.07, 0.28, 0.14, 0.06, 0.32, 0.11, 0.26, 0.19];

function Waveform({ playing }: { playing: boolean }) {
  return (
    <div className="flex items-center gap-[2px] h-4">
      {BAR_HEIGHTS.map((h, i) => (
        <div
          key={i}
          className={`w-[3px] rounded-full ${playing ? "bg-orange-500 waveform-bar" : "bg-gray-200"}`}
          style={{
            height: playing ? `${h}%` : "20%",
            animationDelay: `${BAR_DELAYS[i]}s`,
            transition: "height 0.3s ease",
          }}
        />
      ))}
    </div>
  );
}

export default function Player({ slot, seekTo, isLive, autoplay = false, onEnded }: Props) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [playing, setPlaying] = useState(false);
  const [currentSec, setCurrentSec] = useState(0);
  const [duration, setDuration] = useState(0);
  const prevSlotId = useRef<string | null>(null);

  const audioSrc = slot?.audio_path ? `/api/media/${slot.audio_path}` : null;

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio || !audioSrc) return;

    if (prevSlotId.current !== slot?.id) {
      audio.src = audioSrc;
      audio.load();
      prevSlotId.current = slot?.id ?? null;

      const onMeta = () => {
        setDuration(audio.duration);
        if (seekTo !== undefined && isLive) audio.currentTime = seekTo;
        if (autoplay) audio.play().then(() => setPlaying(true)).catch(() => {});
      };
      audio.addEventListener("loadedmetadata", onMeta, { once: true });
      return () => audio.removeEventListener("loadedmetadata", onMeta);
    }
  }, [slot?.id, audioSrc, seekTo, isLive, autoplay]);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio || !audioSrc || !isLive) return;
    if (seekTo !== undefined && Math.abs(audio.currentTime - seekTo) > 2) {
      audio.currentTime = seekTo;
    }
  }, [seekTo, isLive, audioSrc]);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;
    const tick = setInterval(() => setCurrentSec(Math.floor(audio.currentTime)), 500);
    return () => clearInterval(tick);
  }, []);

  function togglePlay() {
    const audio = audioRef.current;
    if (!audio) return;
    if (audio.paused) {
      audio.play().then(() => setPlaying(true)).catch(() => {});
    } else {
      audio.pause();
      setPlaying(false);
    }
  }

  function handleSeek(e: React.ChangeEvent<HTMLInputElement>) {
    if (isLive) return;
    const audio = audioRef.current;
    if (!audio) return;
    const newTime = Number(e.target.value);
    audio.currentTime = newTime;
    setCurrentSec(newTime);
  }

  const pct = duration > 0 ? (currentSec / duration) * 100 : 0;
  const totalSec = Math.floor(duration) || slot?.duration_sec || 0;

  if (!slot) {
    return (
      <div className="flex items-center gap-3 py-2 text-gray-300">
        <div className="w-12 h-12 rounded-full bg-gray-100 border-2 border-gray-300 flex items-center justify-center">
          <Play className="w-5 h-5 text-gray-400" />
        </div>
        <span className="text-sm text-gray-400">No show currently on air</span>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      <audio
        ref={audioRef}
        onPlay={() => setPlaying(true)}
        onPause={() => setPlaying(false)}
        onLoadedMetadata={(e) => setDuration((e.target as HTMLAudioElement).duration)}
        onEnded={() => { setPlaying(false); onEnded?.(); }}
      />

      <Waveform playing={playing} />

      <div className="flex items-center gap-4">
        <button
          onClick={togglePlay}
          className={`relative w-9 h-9 rounded-full flex items-center justify-center text-white shrink-0 transition-all duration-200 cursor-pointer active:scale-95 hover:scale-105 border-2
            ${playing
              ? "bg-orange-500 shadow-xl shadow-orange-500/30 hover:bg-orange-400 border-orange-400"
              : "bg-gray-900 hover:bg-gray-700 shadow-lg border-gray-700"
            }`}
        >
          {playing
            ? <Pause className="w-4 h-4" />
            : <Play className="w-4 h-4 ml-0.5" />}
        </button>

        <div className="flex-1">
          {isLive ? (
            <LiveProgress slot={slot} seekTo={seekTo ?? 0} />
          ) : (
            <div className="flex flex-col gap-1.5">
              <div className="relative h-2 bg-gray-200 rounded-full overflow-visible border border-gray-300">
                <div
                  className="absolute left-0 top-0 h-full bg-gradient-to-r from-orange-500 to-orange-400 rounded-full transition-all duration-500"
                  style={{ width: `${pct}%` }}
                />
                <input
                  type="range"
                  min={0}
                  max={totalSec}
                  value={currentSec}
                  onChange={handleSeek}
                  className="absolute inset-0 w-full opacity-0 cursor-pointer h-full"
                />
              </div>
              <div className="flex justify-between text-[11px] font-mono text-gray-400 tabular-nums">
                <span>{formatDuration(currentSec)}</span>
                <span>{formatDuration(totalSec)}</span>
              </div>
            </div>
          )}
        </div>

        <Volume2 className="w-4 h-4 text-gray-300 shrink-0" />
      </div>

      {!audioSrc && (
        <p className="text-xs text-gray-400 italic">
          Audio unavailable — generating…
        </p>
      )}
    </div>
  );
}
