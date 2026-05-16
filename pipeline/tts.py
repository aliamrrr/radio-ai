from __future__ import annotations

import io
import re
import struct

import httpx
import lameenc
import numpy as np
import soundfile as sf
from tenacity import retry, stop_after_attempt, wait_exponential

from pipeline import config
from pipeline.schema import Slot
from pipeline.utils import get_logger

logger = get_logger(__name__)

SILENCE_MS = 200
_TTS_URL = "https://api.gradium.ai/api/post/speech/tts"


# ── Audio helpers ─────────────────────────────────────────────────────────────

def _wav_bytes_to_array(wav_bytes: bytes) -> tuple[np.ndarray, int]:
    """Return (int16 samples, samplerate). Always mono int16."""
    data, sr = sf.read(io.BytesIO(wav_bytes), dtype="int16", always_2d=False)
    if data.ndim == 2:
        data = data.mean(axis=1).astype(np.int16)  # stereo → mono
    return data, sr


def _silence_array(samplerate: int, ms: int = SILENCE_MS) -> np.ndarray:
    n_samples = int(samplerate * ms / 1000)
    return np.zeros(n_samples, dtype=np.int16)


def _encode_mp3(samples: np.ndarray, samplerate: int, bitrate: int = 128) -> bytes:
    encoder = lameenc.Encoder()
    encoder.set_bit_rate(bitrate)
    encoder.set_in_sample_rate(samplerate)
    encoder.set_channels(1)
    encoder.set_quality(2)
    chunks = encoder.encode(samples.tobytes())
    chunks += encoder.flush()
    return chunks


def _generate_silent_mp3(duration_sec: int, samplerate: int = 22050) -> bytes:
    samples = np.zeros(duration_sec * samplerate, dtype=np.int16)
    return _encode_mp3(samples, samplerate)


# ── Gradium API ───────────────────────────────────────────────────────────────

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def _call_gradium_tts(text: str, voice_id: str) -> bytes:
    """POST to Gradium TTS. Returns raw WAV bytes."""
    headers = {
        "x-api-key": config.GRADIUM_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "text": text,
        "voice_id": voice_id,
        "output_format": "wav",
        "only_audio": True,
    }
    with httpx.Client(timeout=120, verify=False) as client:
        resp = client.post(_TTS_URL, json=payload, headers=headers)
        resp.raise_for_status()
        return resp.content


def _get_voice(name: str) -> str:
    voice = config.VOICE_MAP.get(name)
    if not voice:
        logger.warning(f"No voice mapping for '{name}', using Lea")
        voice = "QY_BJKHMElKDO12-"  # Lea — French female default
    return voice


_MAX_TTS_CHARS = 900


def _chunk_text(text: str, max_chars: int = _MAX_TTS_CHARS) -> list[str]:
    """Split text into chunks <= max_chars, breaking on sentence boundaries."""
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    chunks: list[str] = []
    current = ""
    for s in sentences:
        # If a single sentence exceeds the limit, split on comma/semicolon
        if len(s) > max_chars:
            sub_parts = re.split(r'(?<=[,;])\s+', s)
            for part in sub_parts:
                if len(current) + len(part) + 1 <= max_chars:
                    current = (current + " " + part).strip() if current else part
                else:
                    if current:
                        chunks.append(current)
                    current = part[:max_chars]
            continue
        if len(current) + len(s) + 1 <= max_chars:
            current = (current + " " + s).strip() if current else s
        else:
            if current:
                chunks.append(current)
            current = s
    if current:
        chunks.append(current)
    return chunks or [text[:max_chars]]


def _parse_dialogue_lines(script: str) -> list[tuple[str, str]]:
    lines: list[tuple[str, str]] = []
    for line in script.splitlines():
        line = line.strip()
        if not line:
            continue
        match = re.match(r"^\[(.+?)\]\s*(.*)", line)
        if match:
            speaker, text = match.group(1).strip(), match.group(2).strip()
            if text:
                lines.append((speaker, text))
        else:
            speaker = lines[-1][0] if lines else "unknown"
            lines.append((speaker, line))
    return lines


# ── Main entrypoint ───────────────────────────────────────────────────────────

def synthesize_slot(slot: Slot, use_stub: bool = False) -> Slot:
    output_path = config.AUDIO_DIR / f"{slot.id}.mp3"
    tmp_path = output_path.with_suffix(".tmp.mp3")
    script = slot.script or ""

    if use_stub or config._is_placeholder(config.GRADIUM_API_KEY):
        logger.warning(f"[tts] GRADIUM_API_KEY not set — silent stub for {slot.id}")
        tmp_path.write_bytes(_generate_silent_mp3(slot.duration_sec))
        tmp_path.replace(output_path)
        return slot.model_copy(update={"audio_path": f"audio/{slot.id}.mp3"})

    try:
        if slot.type_script in ("dialogue", "debate"):
            lines = _parse_dialogue_lines(script)
            segments: list[np.ndarray] = []
            samplerate = 22050  # will be overwritten by first real segment

            for speaker, text in lines:
                voice = _get_voice(speaker)
                logger.info(f"[tts] {slot.id} [{speaker}] {len(text)} chars")
                wav_bytes = _call_gradium_tts(text, voice)
                arr, samplerate = _wav_bytes_to_array(wav_bytes)
                segments.append(arr)
                segments.append(_silence_array(samplerate))

            combined = np.concatenate(segments) if segments else np.zeros(0, dtype=np.int16)
            mp3_bytes = _encode_mp3(combined, samplerate)

        else:
            host = slot.noms[0]
            voice = _get_voice(host)
            chunks = _chunk_text(script)
            logger.info(f"[tts] {slot.id} [{host}] {len(script)} chars -> {len(chunks)} chunks")
            samplerate = 22050
            segments: list[np.ndarray] = []
            for chunk in chunks:
                wav_bytes = _call_gradium_tts(chunk, voice)
                arr, samplerate = _wav_bytes_to_array(wav_bytes)
                segments.append(arr)
                segments.append(_silence_array(samplerate, ms=100))
            combined = np.concatenate(segments) if segments else np.zeros(0, dtype=np.int16)
            mp3_bytes = _encode_mp3(combined, samplerate)

        tmp_path.write_bytes(mp3_bytes)

    except Exception as exc:
        logger.error(f"[tts] Failed for {slot.id}: {exc} — silent fallback")
        tmp_path.write_bytes(_generate_silent_mp3(slot.duration_sec))

    tmp_path.replace(output_path)
    logger.info(f"[tts] Saved: audio/{slot.id}.mp3")
    return slot.model_copy(update={"audio_path": f"audio/{slot.id}.mp3"})
