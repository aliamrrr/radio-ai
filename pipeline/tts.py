from __future__ import annotations

import io
import os
import re
import shutil
import tempfile

import httpx
import lameenc
import numpy as np
import soundfile as sf
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from pipeline import config
from pipeline.schema import Slot
from pipeline.utils import get_logger

logger = get_logger(__name__)

SILENCE_MS = 200
_TTS_URL = "https://api.gradium.ai/api/post/speech/tts"

# OpenAI TTS voices — short names trigger OpenAI, long base64-style IDs use Gradium
_OPENAI_VOICES = {"alloy", "ash", "ballad", "coral", "echo", "fable", "nova", "onyx", "sage", "shimmer"}


# ── Audio helpers ─────────────────────────────────────────────────────────────

def _wav_bytes_to_array(wav_bytes: bytes) -> tuple[np.ndarray, int]:
    data, sr = sf.read(io.BytesIO(wav_bytes), dtype="int16", always_2d=False)
    if data.ndim == 2:
        data = data.mean(axis=1).astype(np.int16)
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


# ── TTS API calls ─────────────────────────────────────────────────────────────

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def _call_openai_tts(text: str, voice: str) -> bytes:
    client = OpenAI(
        api_key=config.OPENAI_API_KEY,
        http_client=httpx.Client(verify=not config.SSL_NO_VERIFY),
    )
    response = client.audio.speech.create(
        model="tts-1",
        voice=voice,  # type: ignore[arg-type]
        input=text,
        response_format="wav",
    )
    return response.content


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def _call_gradium_tts(text: str, voice_id: str) -> bytes:
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
    with httpx.Client(timeout=120, verify=not config.SSL_NO_VERIFY) as client:
        resp = client.post(_TTS_URL, json=payload, headers=headers)
        resp.raise_for_status()
        return resp.content


def _call_tts(text: str, voice: str) -> bytes:
    if voice in _OPENAI_VOICES:
        return _call_openai_tts(text, voice)
    return _call_gradium_tts(text, voice)


def _get_voice(name: str) -> str:
    voice = config.VOICE_MAP.get(name)
    if not voice:
        logger.warning(f"No voice mapping for '{name}', defaulting to nova")
        voice = "nova"
    return voice


_MAX_TTS_CHARS = 900


def _chunk_text(text: str, max_chars: int = _MAX_TTS_CHARS) -> list[str]:
    """Split text into chunks <= max_chars, breaking on sentence boundaries."""
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    chunks: list[str] = []
    current = ""
    for s in sentences:
        if len(s) > max_chars:
            # Fix ReDoS: use negated char class instead of .+ with lazy quantifier
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
        # Fix ReDoS: use [^\]]+ (negated char class) instead of .+? (lazy dot)
        match = re.match(r"^\[([^\]]{1,100})\]\s*(.*)", line)
        if match:
            speaker, text = match.group(1).strip(), match.group(2).strip()
            if text:
                lines.append((speaker, text))
        else:
            speaker = lines[-1][0] if lines else "unknown"
            lines.append((speaker, line))
    return lines


# ── Atomic file write helper ──────────────────────────────────────────────────

def _write_mp3_atomic(mp3_bytes: bytes, dest_path) -> None:
    """Write bytes to a temp file then atomically move it to dest_path."""
    tmp_fd, tmp_name = tempfile.mkstemp(suffix=".mp3", dir=str(dest_path.parent))
    try:
        with os.fdopen(tmp_fd, "wb") as f:
            f.write(mp3_bytes)
            f.flush()
            os.fsync(f.fileno())
        shutil.move(tmp_name, str(dest_path))
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


# ── Main entrypoint ───────────────────────────────────────────────────────────

def synthesize_slot(slot: Slot, use_stub: bool = False) -> Slot:
    output_path = config.AUDIO_DIR / f"{slot.id}_raw.mp3"
    script = slot.script or ""

    if use_stub or config._is_placeholder(config.OPENAI_API_KEY):
        logger.warning(f"[tts] API key not set — silent stub for {slot.id}")
        _write_mp3_atomic(_generate_silent_mp3(slot.duration_int or 60), output_path)
        return slot.model_copy(update={"audio_path": f"audio/{slot.id}_raw.mp3"})

    try:
        if slot.type_script in ("dialogue", "debate"):
            lines = _parse_dialogue_lines(script)
            segments: list[np.ndarray] = []
            samplerate = 22050

            for speaker, text in lines:
                voice = _get_voice(speaker)
                logger.info(f"[tts] {slot.id} [{speaker}] {len(text)} chars")
                wav_bytes = _call_tts(text, voice)
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
            segments = []
            for chunk in chunks:
                wav_bytes = _call_tts(chunk, voice)
                arr, samplerate = _wav_bytes_to_array(wav_bytes)
                segments.append(arr)
                segments.append(_silence_array(samplerate, ms=100))
            combined = np.concatenate(segments) if segments else np.zeros(0, dtype=np.int16)
            mp3_bytes = _encode_mp3(combined, samplerate)

    except Exception as exc:
        logger.error(f"[tts] Failed for {slot.id}: {exc} — silent fallback", exc_info=True)
        mp3_bytes = _generate_silent_mp3(slot.duration_int or 60)

    _write_mp3_atomic(mp3_bytes, output_path)
    logger.info(f"[tts] Saved: audio/{slot.id}_raw.mp3")

    # Upload raw audio to R2 if configured (final merge happens in audio_producer)
    from pipeline import storage  # deferred import
    audio_path = f"audio/{slot.id}_raw.mp3"
    if storage.is_configured():
        try:
            storage.upload_file(output_path, audio_path)
        except Exception as exc:
            logger.error(f"[tts] R2 upload failed for {slot.id}: {exc}", exc_info=True)

    return slot.model_copy(update={"audio_path": audio_path})
