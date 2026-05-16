from __future__ import annotations

import random
from datetime import datetime, timezone
from pathlib import Path

import imageio_ffmpeg
from pydub import AudioSegment

from pipeline import config
from pipeline.schema import Slot
from pipeline.utils import get_logger

logger = get_logger(__name__)

# Point pydub to bundled ffmpeg — no system install required
AudioSegment.converter = imageio_ffmpeg.get_ffmpeg_exe()

# Map thematique → intro filename (handles space vs underscore mismatches)
_INTRO_MAP: dict[str, str] = {
    "international news": "international news_intro.mp3",
    "tech & ai":          "tech & AI_intro.mp3",
    "culture":            "culture_intro.mp3",
    "lifestyle":          "lifestyle_intro.mp3",
    "sport":              "sport_intro.mp3",
    "sports":             "sport_intro.mp3",
    "music":              "music_intro.mp3",
}


def _mp3(path: Path) -> AudioSegment:
    return AudioSegment.from_mp3(str(path))


def _resolve_asset(relative: str) -> Path:
    """Resolve a relative asset path from programme JSON, with flexible name matching."""
    base = config.RADIO_ASSETS_DIR
    direct = base / relative
    if direct.exists():
        return direct
    # Flexible: compare stems normalized (lower, underscores→spaces)
    folder = base / Path(relative).parent
    target = Path(relative).stem.lower().replace("_", " ")
    for f in folder.glob("*.mp3"):
        if f.stem.lower().replace("_", " ") == target:
            return f
    raise FileNotFoundError(f"Asset not found: {relative} (looked in {folder})")


def _intro_path(thematique: str) -> Path | None:
    filename = _INTRO_MAP.get(thematique.lower())
    if not filename:
        return None
    p = config.RADIO_ASSETS_DIR / "intros_songs" / filename
    if p.exists():
        return p
    # Fallback: glob
    for f in (config.RADIO_ASSETS_DIR / "intros_songs").glob("*.mp3"):
        if thematique.lower().split()[0] in f.name.lower():
            return f
    return None


def merge_show_audio(slot: Slot) -> Slot:
    """
    intro.mp3 + {id}_raw.mp3 + outro.mp3  →  {id}.mp3
    Returns updated slot with audio_path, intro_duration_sec, outro_duration_sec, duration_sec.
    """
    raw_path = config.AUDIO_DIR / f"{slot.id}_raw.mp3"
    if not raw_path.exists():
        logger.warning(f"[audio] {slot.id}: _raw.mp3 not found — skipping merge")
        return slot

    segments: list[AudioSegment] = []
    intro_dur = 0
    outro_dur = 0

    # ── Intro ────────────────────────────────────────────────────────────────
    intro_p: Path | None = None
    if slot.intro_audio_path:
        try:
            intro_p = _resolve_asset(slot.intro_audio_path)
        except FileNotFoundError:
            intro_p = _intro_path(slot.thematique)
    else:
        intro_p = _intro_path(slot.thematique)

    if intro_p:
        seg = _mp3(intro_p)
        intro_dur = int(len(seg) / 1000)
        segments.append(seg)
        logger.info(f"[audio] {slot.id} intro  {intro_dur}s  ({intro_p.name})")

    # ── Script ───────────────────────────────────────────────────────────────
    segments.append(_mp3(raw_path))

    # ── Outro ────────────────────────────────────────────────────────────────
    outro_p: Path | None = None
    if slot.outro_audio_path:
        try:
            outro_p = _resolve_asset(slot.outro_audio_path)
        except FileNotFoundError:
            outro_p = intro_p
    else:
        outro_p = intro_p  # same as intro by default

    if outro_p:
        seg = _mp3(outro_p)
        outro_dur = int(len(seg) / 1000)
        segments.append(seg)
        logger.info(f"[audio] {slot.id} outro  {outro_dur}s  ({outro_p.name})")

    # ── Merge & export ───────────────────────────────────────────────────────
    final = segments[0]
    for s in segments[1:]:
        final += s

    out = config.AUDIO_DIR / f"{slot.id}.mp3"
    final.export(str(out), format="mp3", bitrate="128k")
    total = int(len(final) / 1000)
    logger.info(f"[audio] {slot.id} → {out.name}  total={total}s")

    return slot.model_copy(update={
        "audio_path":         f"audio/{slot.id}.mp3",
        "intro_duration_sec": intro_dur,
        "outro_duration_sec": outro_dur,
        "duration_sec":       total,
    })


def fill_music_gap(slot: Slot, gap_sec: int) -> Slot:
    """
    Pick a random overlap song, loop/trim it to gap_sec, export as {id}.mp3.
    """
    if gap_sec <= 0:
        logger.warning(f"[audio] {slot.id}: gap_sec={gap_sec}, nothing to fill")
        return slot

    overlap_dir = config.RADIO_ASSETS_DIR / "overlap_music_songs"
    files = sorted(overlap_dir.glob("*.mp3"))
    if not files:
        logger.error(f"[audio] No overlap songs in {overlap_dir}")
        return slot

    chosen = random.choice(files)
    logger.info(f"[audio] {slot.id} gap={gap_sec}s  using {chosen.name}")

    music = _mp3(chosen)
    while len(music) < gap_sec * 1000:
        music += _mp3(chosen)

    music = music[: gap_sec * 1000]
    if gap_sec > 5:
        music = music.fade_out(min(3000, len(music) // 2))

    out = config.AUDIO_DIR / f"{slot.id}.mp3"
    music.export(str(out), format="mp3", bitrate="128k")
    logger.info(f"[audio] {slot.id} → {out.name}  ({gap_sec}s)")

    return slot.model_copy(update={
        "audio_path":        f"audio/{slot.id}.mp3",
        "duration_sec":      gap_sec,
        "last_generated_at": datetime.now(timezone.utc),
    })


def process_all_audio(slots: list[Slot]) -> list[Slot]:
    """
    Run audio production for every slot:
    - Show slots  → merge intro + raw_script + outro
    - Music slots → fill gap with random overlap song
    """
    ordered = sorted(slots, key=lambda s: s.start_seconds())
    slot_map = {s.id: s for s in slots}

    for i, slot in enumerate(ordered):
        if slot.is_music:
            nxt = ordered[i + 1] if i + 1 < len(ordered) else None
            gap_sec = (nxt.start_seconds() - slot.start_seconds()) if nxt else 300
            slot_map[slot.id] = fill_music_gap(slot, max(0, gap_sec))
        else:
            slot_map[slot.id] = merge_show_audio(slot)

    return [slot_map[s.id] for s in slots]
