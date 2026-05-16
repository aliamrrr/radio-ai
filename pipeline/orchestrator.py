from __future__ import annotations

import json
import os
from datetime import date

from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential

from pipeline import config
from pipeline.schema import Slot
from pipeline.utils import get_logger

logger = get_logger(__name__)


def _get_client() -> genai.Client:
    import httpx
    client = genai.Client(api_key=config.GOOGLE_API_KEY)
    # Bypass SSL verification (needed when corporate proxy intercepts TLS)
    client._api_client._httpx_client = httpx.Client(verify=False)
    return client


def _extract_json(text: str) -> dict:
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end])
        except json.JSONDecodeError:
            pass
    return {}


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def _call_agent(thematique: str, today: str) -> list[str]:
    """
    Query Generator Agent — uses Gemini to generate targeted web search queries.
    """
    client = _get_client()

    response = client.models.generate_content(
        model=config.GEMINI_MODEL,
        contents=(
            f"Thematic: {thematique}\n"
            f"Today's date: {today}\n"
            "Generate 2-3 specific web search queries for a French radio audience."
        ),
        config=types.GenerateContentConfig(
            system_instruction=(
                "You are a radio content researcher. Given a thematic area and today's date, "
                "generate 2-3 specific web search queries to find the most current and relevant "
                "news or content for a French radio audience. "
                'Return ONLY valid JSON, no markdown fences: {"queries": ["query1", "query2", ...]}'
            ),
            temperature=0.7,
        ),
    )
    return _extract_json(response.text or "").get("queries", [])


def generate_queries(slots: list[Slot]) -> dict[str, list[str]]:
    config.require_key("GOOGLE_API_KEY", config.GOOGLE_API_KEY)
    today = date.today().isoformat()

    themes = list({slot.thematique for slot in slots})
    logger.info(f"Generating search queries for {len(themes)} themes: {themes}")

    result: dict[str, list[str]] = {}
    for theme in themes:
        logger.info(f"  Querying theme: {theme}")
        queries = _call_agent(theme, today)
        result[theme] = queries
        logger.info(f"  Got {len(queries)} queries for '{theme}'")

    return result
