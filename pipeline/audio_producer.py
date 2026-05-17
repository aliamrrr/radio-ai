from __future__ import annotations

import os
import random
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import imageio_ffmpeg
from pydub import AudioSegment

from pipeline import config
from pipeline.schema import Slot
from pipeline.utils import get_logger

logger = get_logger(__name__)

# Point pydub to bundled ffmpeg for encoding — no system install required
_FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
AudioSegment.converter = _FFMPEG

_INTRO_MAP: dict[str, str] = {
    "international news": "international news_intro.mp3",
    "tech & ai":          "tech & AI_intro.mp3",
    "culture":            "culture_intro.mp3",
    "lifestyle":          "lifestyle_intro.mp3",
    "sport":              "sport_intro.mp3",
    "sports":             "sport_intro.mp3",
    "music":              "music_intro.mp3",
}

# Safety cap: prevents unbounded memory growth when concatenating audio
_MAX_LOOP_ITER = 200
_MAX_GAP_SEC = 1800  # 30 min max gap fill


def _mp3(path: Path) -> AudioSegment:
    cmd = [
        _FFMPEG, "-v", "error", "-i", str(path),
        "-f", "s16le", "-acodec", "pcm_s16le", "-ac", "1", "-ar", "22050", "pipe:1",
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg decode failed for {path.name}: {proc.stderr.decode()}")
    return AudioSegment(data=proc.stdout, sample_width=2, frame_rate=22050, channels=1)


def _resolve_asset(relative: str) -> Path:
    base = config.RADIO_ASSETS_DIR
    direct = base / relative
    if direct.exists():
        return direct
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
    for f in (config.RADIO_ASSETS_DIR / "intros_songs").glob("*.mp3"):
        if thematique.lower().split()[0] in f.name.lower():
            return f
    return None


def _export_atomic(segment: AudioSegment, dest: Path, bitrate: str = "128k") -> None:
    """Export AudioSegment to dest atomically via a temp file."""
    tmp_fd, tmp_name = tempfile.mkstemp(suffix=".mp3", dir=str(dest.parent))
    try:
        os.close(tmp_fd)
        segment.export(tmp_name, format="mp3", bitrate=bitrate)
        shutil.move(tmp_name, str(dest))
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


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
        outro_p = intro_p

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
    _export_atomic(final, out)
    total = int(len(final) / 1000)
    logger.info(f"[audio] {slot.id} -> {out.name}  total={total}s")

    from pipeline import storage  # deferred import
    audio_key = f"audio/{slot.id}.mp3"
    audio_path: str = audio_key
    if storage.is_configured():
        try:
            audio_path = storage.upload_file(out, audio_key)
        except Exception as exc:
            logger.error(f"[audio] R2 upload failed for {slot.id}: {exc}", exc_info=True)

    return slot.model_copy(update={
        "audio_path":         audio_path,
        "intro_duration_sec": intro_dur,
        "outro_duration_sec": outro_dur,
        "duration_sec":       total,
    })


def fill_music_gap(slot: Slot, gap_sec: int) -> Slot:
    """Pick a random overlap song, loop/trim it to gap_sec, export as {id}.mp3."""
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
    iterations = 0
    while len(music) < gap_sec * 1000:
        iterations += 1
        if iterations >= _MAX_LOOP_ITER:
            logger.warning(f"[audio] {slot.id}: hit loop cap ({_MAX_LOOP_ITER}), truncating")
            break
        music += _mp3(chosen)

    music = music[: gap_sec * 1000]
    if gap_sec > 5:
        music = music.fade_out(min(3000, len(music) // 2))

    out = config.AUDIO_DIR / f"{slot.id}.mp3"
    _export_atomic(music, out)
    logger.info(f"[audio] {slot.id} -> {out.name}  ({gap_sec}s)")

    from pipeline import storage  # deferred import
    audio_key = f"audio/{slot.id}.mp3"
    audio_path: str = audio_key
    if storage.is_configured():
        try:
            audio_path = storage.upload_file(out, audio_key)
        except Exception as exc:
            logger.error(f"[audio] R2 upload failed for {slot.id}: {exc}", exc_info=True)

    return slot.model_copy(update={
        "audio_path":        audio_path,
        "duration_sec":      gap_sec,
        "last_generated_at": datetime.now(timezone.utc),
    })


def process_all_audio(slots: list[Slot]) -> list[Slot]:
    """
    For each show slot: merge intro + raw_script + outro.
    Automatically detect gaps and fill them with random overlap songs.
    Returns original slots + auto-generated gap slots, sorted by start time.
    """
    show_slots = sorted(
        [s for s in slots if not s.is_music],
        key=lambda s: s.start_seconds(),
    )
    result: list[Slot] = []

    for i, slot in enumerate(show_slots):
        merged = merge_show_audio(slot)
        result.append(merged)

        if i + 1 < len(show_slots):
            nxt = show_slots[i + 1]
            show_end_sec = slot.start_seconds() + merged.duration_int
            gap_sec = nxt.start_seconds() - show_end_sec

            if 2 < gap_sec <= _MAX_GAP_SEC:
                h, m = divmod(show_end_sec // 60, 60)
                gap_time = f"{h:02d}:{m:02d}"
                gap_id = f"gap_{gap_time.replace(':', '')}"
                gap_slot = Slot(
                    id=gap_id,
                    start_time=gap_time,
                    duration_sec=gap_sec,
                    thematique="music",
                    type_script="music",
                    title="music break",
                )
                result.append(fill_music_gap(gap_slot, gap_sec))
                logger.info(f"[audio] auto gap {gap_time} -> {gap_sec}s filler inserted")
            elif gap_sec > _MAX_GAP_SEC:
                logger.warning(f"[audio] gap {gap_sec}s > {_MAX_GAP_SEC}s — skipping gap fill")

    return result
