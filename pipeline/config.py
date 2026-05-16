from __future__ import annotations

import os
from pathlib import Path

import certifi
from dotenv import load_dotenv

load_dotenv()

# Fix SSL cert verification on Windows
os.environ.setdefault("SSL_CERT_FILE", certifi.where())
os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())

# Resolve paths relative to the repo root (one level above pipeline/)
_ROOT = Path(__file__).parent.parent

PROGRAMME_PATH = Path(os.getenv("PROGRAMME_PATH", str(_ROOT / "programme.json")))
MEDIA_DIR = Path(os.getenv("MEDIA_DIR", str(_ROOT / "media")))
IMAGES_DIR = MEDIA_DIR / "images"
AUDIO_DIR = MEDIA_DIR / "audio"
LOGS_DIR = _ROOT / "logs"
RADIO_ASSETS_DIR = Path(os.getenv("RADIO_ASSETS_DIR", str(_ROOT.parent / "programme_radio")))

TIMEZONE = os.getenv("TIMEZONE", "Europe/Paris")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")

GRADIUM_API_KEY = os.getenv("GRADIUM_API_KEY", "")
GRADIUM_BASE_URL = os.getenv("GRADIUM_BASE_URL", "https://api.gradium.example/v1")

FAL_API_KEY = os.getenv("FAL_API_KEY", "")
FAL_MODEL = os.getenv("FAL_MODEL", "fal-ai/flux/schnell")
FAL_PROMPT_PATH = Path(os.getenv("FAL_PROMPT_PATH", str(_ROOT.parent / "prompts" / "prompt-fal.txt")))

_raw_voice_map = os.getenv(
    "VOICE_MAP",
    "Claire=voice_fr_female_1,Marc=voice_fr_male_1,Léa=voice_fr_female_2,"
    "Sofia=voice_fr_female_3,Tom=voice_fr_male_2,Inès=voice_fr_female_4,Hugo=voice_fr_male_3,"
    "Yanis=voice_fr_male_4,Emma=voice_fr_female_5",
)
VOICE_MAP: dict[str, str] = dict(
    pair.split("=", 1) for pair in _raw_voice_map.split(",") if "=" in pair
)


def _is_placeholder(key: str) -> bool:
    return not key or "REPLACE_ME" in key


def require_key(name: str, value: str) -> str:
    if _is_placeholder(value):
        raise RuntimeError(
            f"Missing API key: {name} is '{value}'. "
            f"Copy .env.example to .env and fill in the real key."
        )
    return value
