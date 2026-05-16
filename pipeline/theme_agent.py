from __future__ import annotations

import json
from typing import Any

from google import genai
from google.genai import types
from tavily import TavilyClient
from tenacity import retry, stop_after_attempt, wait_exponential

from pipeline import config
from pipeline.schema import Slot
from pipeline.utils import get_logger

logger = get_logger(__name__)

WORDS_PER_MINUTE = 150


def _target_word_count(duration_sec: int) -> int:
    return int(duration_sec / 60 * WORDS_PER_MINUTE)


def _build_context(results: list[dict[str, Any]]) -> str:
    parts = []
    for r in results:
        parts.append(
            f"Source: {r.get('title', '')}\nURL: {r.get('url', '')}\n{r.get('content', '')}"
        )
    return "\n\n---\n\n".join(parts)


def _extract_json(text: str) -> dict:
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end])
        except json.JSONDecodeError:
            pass
    return {}


def _format_noms(noms: list[str]) -> str:
    return ", ".join(noms)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def _generate_script(slot: Slot, context: str, search_fn) -> dict[str, str]:
    """
    Script Writer Agent — Gemini with Tavily search tool.
    Uses automatic function calling: the model can call search_web as needed.
    """
    word_count = _target_word_count(slot.duration_sec)
    noms_str = _format_noms(slot.noms)

    if slot.type_script in ("dialogue", "debate"):
        format_instructions = (
            f"MANDATORY: use speaker tags on separate lines:\n"
            f"[{slot.noms[0]}] Bonjour à tous...\n"
            f"[{slot.noms[1] if len(slot.noms) > 1 else slot.noms[0]}] Oui exactement...\n"
            "Alternate speakers naturally throughout."
        )
    else:
        format_instructions = (
            f"Write plain prose for a single speaker ({slot.noms[0]}). No speaker tags."
        )

    system_instruction = (
        f"You are a professional French radio scriptwriter. "
        f"Write engaging, natural-sounding radio scripts in {slot.langue}. "
        "You have access to a search_web tool — use it to find additional fresh information if needed. "
        'Return ONLY valid JSON, no markdown fences: '
        '{"sujet": "<topic title, max 2 lines>", "script": "<full script text>"}'
    )

    prompt = (
        f"Theme: {slot.thematique}\n"
        f"Format: {slot.type_script}\n"
        f"Hosts: {noms_str}\n"
        f"Duration: {slot.duration_sec}s (~{word_count} words)\n"
        f"Language: {slot.langue}\n\n"
        f"Format instructions:\n{format_instructions}\n\n"
        f"Web context already gathered:\n{context}\n\n"
        f"Write a {slot.type_script} script of approximately {word_count} words."
    )

    # Define Tavily as an ADK-style tool function
    def search_web(query: str) -> str:
        """Search the web for recent news and information on a given topic."""
        return search_fn(query)

    import httpx
    client = genai.Client(api_key=config.GOOGLE_API_KEY)
    # Bypass SSL verification (needed when corporate proxy intercepts TLS)
    client._api_client._httpx_client = httpx.Client(verify=False)

    # Automatic function calling: Gemini calls search_web autonomously if needed
    response = client.models.generate_content(
        model=config.GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            tools=[search_web],
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=False),
            temperature=0.8,
        ),
    )

    result = _extract_json(response.text or "")
    if not result.get("script"):
        raise ValueError(f"Empty script returned by model for slot {slot.id!r} — will retry")
    return result


def process_theme(thematique: str, queries: list[str], slots: list[Slot]) -> list[Slot]:
    config.require_key("GOOGLE_API_KEY", config.GOOGLE_API_KEY)
    config.require_key("TAVILY_API_KEY", config.TAVILY_API_KEY)

    tavily = TavilyClient(api_key=config.TAVILY_API_KEY)
    tavily.session.verify = False  # bypass corporate proxy SSL

    logger.info(f"[{thematique}] Searching {len(queries)} queries...")
    all_results: list[dict] = []
    for q in queries:
        res = tavily.search(query=q, search_depth="advanced", max_results=3, include_raw_content=False, days=3)
        results = res.get("results", [])
        all_results.extend(results)
        logger.info(f"  [{thematique}] '{q}' -> {len(results)} results")

    context = _build_context(all_results)

    def search_fn(query: str) -> str:
        res = tavily.search(query=query, search_depth="advanced", max_results=3, days=3)
        parts = [
            f"Title: {r.get('title', '')}\nURL: {r.get('url', '')}\n{r.get('content', '')}"
            for r in res.get("results", [])
        ]
        return "\n\n---\n\n".join(parts) if parts else "No results found."

    updated_slots = []
    for slot in slots:
        if slot.thematique != thematique:
            updated_slots.append(slot)
            continue

        logger.info(f"[{thematique}] Generating script for slot {slot.id}...")
        try:
            data = _generate_script(slot, context, search_fn)
            slot = slot.model_copy(
                update={"sujet": data.get("sujet", ""), "script": data.get("script", "")}
            )
            logger.info(f"[{thematique}] Slot {slot.id} done - {len(slot.script or '')} chars")
        except Exception as exc:
            logger.error(f"[{thematique}] Script generation failed for {slot.id}: {exc} — keeping existing script")
        updated_slots.append(slot)

    return updated_slots
