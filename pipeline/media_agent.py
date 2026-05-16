from __future__ import annotations

import os
import re
import time
from pathlib import Path

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from pipeline import config
from pipeline.schema import Slot
from pipeline.utils import get_logger

logger = get_logger(__name__)

# Primary model: OpenAI GPT Image 2 via fal.ai
_MODEL_PRIMARY = "fal-ai/gpt-image-2"
# Fallback model: nano-banana-2
_MODEL_FALLBACK = "fal-ai/nano-banana-2"

_PROMPT_FALLBACK = (
    "MS Paint style childlike radio show illustration. "
    "Theme: {thematique}. Subject: {sujet}. Format: {format}. "
    "Crude wobbly outlines, flat colors, ON AIR sign, clock, plant in background."
)


def _build_image_prompt(slot: Slot) -> str:
    format_str = "duo" if slot.nb_intervenants > 1 else "solo"
    sujet = slot.sujet or slot.thematique
    thematique = slot.thematique

    prompt_path: Path = config.FAL_PROMPT_PATH
    if not prompt_path.exists():
        logger.warning(f"[media] Prompt template not found at {prompt_path}, using fallback.")
        return _PROMPT_FALLBACK.format(thematique=thematique, sujet=sujet, format=format_str)

    template = prompt_path.read_text(encoding="utf-8")

    template = re.sub(r"- Th[eé]matique\s*:\s*\{[^}]+\}", f"- Thématique : {thematique}", template)
    template = re.sub(r"- Sujet\s*:\s*\{[^}]+\}", f"- Sujet : {sujet}", template)
    template = re.sub(r"- Format\s*:\s*\{[^}]+\}", f"- Format : {format_str}", template)

    return template


def _build_payload(model: str, prompt: str) -> dict:
    """Build model-appropriate payload — GPT Image models don't take SD-specific params."""
    if "gpt-image" in model:
        return {"prompt": prompt, "image_size": "1024x1024"}
    return {"prompt": prompt, "image_size": "square_hd", "num_inference_steps": 4, "num_images": 1}


def _submit_and_poll(model: str, prompt: str, headers: dict) -> str:
    """Submit image job to fal.ai queue and return the CDN image URL."""
    payload = _build_payload(model, prompt)

    with httpx.Client(timeout=30, verify=False) as client:
        resp = client.post(f"https://queue.fal.run/{model}", json=payload, headers=headers)
        resp.raise_for_status()
        queue_data = resp.json()
        status_url = queue_data["status_url"]
        result_url = queue_data["response_url"]

    for _ in range(90):
        with httpx.Client(timeout=15, verify=False) as client:
            sr = client.get(status_url, headers=headers, params={"logs": 0})
            sr.raise_for_status()
            status = sr.json().get("status", "")
        if status == "COMPLETED":
            break
        if status == "FAILED":
            raise RuntimeError(f"fal.ai job failed: {sr.json()}")
        time.sleep(2)
    else:
        raise RuntimeError(f"fal.ai job timed out after 180s (model={model})")

    with httpx.Client(timeout=15, verify=False) as client:
        rr = client.get(result_url, headers=headers)
        rr.raise_for_status()
        result = rr.json()

    images = result.get("images") or result.get("image", [])
    if not images:
        raise RuntimeError(f"fal.ai returned no images: {result}")

    img = images[0]
    return img["url"] if isinstance(img, dict) else img


@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=8))
def _call_fal_primary(prompt: str, headers: dict) -> str:
    return _submit_and_poll(_MODEL_PRIMARY, prompt, headers)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def _call_fal_fallback(prompt: str, headers: dict) -> str:
    return _submit_and_poll(_MODEL_FALLBACK, prompt, headers)


def generate_image(slot: Slot) -> Slot:
    config.require_key("FAL_API_KEY", config.FAL_API_KEY)

    prompt = _build_image_prompt(slot)
    format_str = "duo" if slot.nb_intervenants > 1 else "solo"
    logger.info(f"[media] Generating image for {slot.id} (format: {format_str}) via {_MODEL_PRIMARY}...")

    headers = {
        "Authorization": f"Key {config.FAL_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        image_url = _call_fal_primary(prompt, headers)
        logger.info(f"[media] {slot.id} -> primary model OK")
    except Exception as primary_exc:
        logger.warning(f"[media] Primary model failed for {slot.id}: {primary_exc} — trying fallback")
        image_url = _call_fal_fallback(prompt, headers)
        logger.info(f"[media] {slot.id} -> fallback model OK")

    # Store the CDN URL directly — UI renders it without disk download
    logger.info(f"[media] Image URL: {image_url[:80]}...")
    return slot.model_copy(update={"image_path": image_url})
