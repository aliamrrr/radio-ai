from __future__ import annotations

import os
import re
import warnings
from pathlib import Path

import certifi
from dotenv import load_dotenv

load_dotenv()

# Fix SSL cert verification on Windows
os.environ.setdefault("SSL_CERT_FILE", certifi.where())
os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())

# Set to true/1/yes ONLY when behind a corporate proxy that intercepts TLS.
# This disables ALL certificate validation — never use in production.
SSL_NO_VERIFY: bool = os.getenv("SSL_NO_VERIFY", "false").lower() in ("1", "true", "yes")
if SSL_NO_VERIFY:
    warnings.warn(
        "SSL_NO_VERIFY is enabled — certificate validation is disabled. "
        "This should never be used in production.",
        stacklevel=1,
    )

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
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")

GRADIUM_API_KEY = os.getenv("GRADIUM_API_KEY", "")
GRADIUM_BASE_URL = os.getenv("GRADIUM_BASE_URL", "https://api.gradium.example/v1")

FAL_API_KEY = os.getenv("FAL_API_KEY", "")
FAL_MODEL = os.getenv("FAL_MODEL", "fal-ai/flux/schnell")
FAL_PROMPT_PATH = Path(os.getenv("FAL_PROMPT_PATH", str(_ROOT.parent / "prompts" / "prompt-fal.txt")))

# ── Cloudflare R2 (production media storage) ──────────────────────────────────
R2_ACCOUNT_ID       = os.getenv("R2_ACCOUNT_ID", "")
R2_ACCESS_KEY_ID    = os.getenv("R2_ACCESS_KEY_ID", "")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY", "")
R2_BUCKET_NAME      = os.getenv("R2_BUCKET_NAME", "")
R2_PUBLIC_URL       = os.getenv("R2_PUBLIC_URL", "")   # e.g. https://pub-xxx.r2.dev

# ── Voice map ─────────────────────────────────────────────────────────────────
_OPENAI_VOICE_NAMES = frozenset({
    "alloy", "ash", "ballad", "coral", "echo", "fable", "nova", "onyx", "sage", "shimmer"
})
_VALID_VOICE_ID = re.compile(r'^[a-zA-Z0-9_\-]{1,100}$')

_raw_voice_map = os.getenv(
    "VOICE_MAP",
    "Claire=voice_fr_female_1,Marc=voice_fr_male_1,Léa=voice_fr_female_2,"
    "Sofia=voice_fr_female_3,Tom=voice_fr_male_2,Inès=voice_fr_female_4,Hugo=voice_fr_male_3,"
    "Yanis=voice_fr_male_4,Emma=voice_fr_female_5",
)

VOICE_MAP: dict[str, str] = {}
for _pair in _raw_voice_map.split(","):
    if "=" not in _pair:
        continue
    _name, _voice_id = _pair.split("=", 1)
    _name = _name.strip()
    _voice_id = _voice_id.strip()
    if not _VALID_VOICE_ID.match(_voice_id):
        raise RuntimeError(
            f"Invalid voice ID for '{_name}': {_voice_id!r}. "
            "Voice IDs must contain only letters, digits, underscores, or hyphens."
        )
    VOICE_MAP[_name] = _voice_id


def _is_placeholder(key: str) -> bool:
    return not key or "REPLACE_ME" in key


def require_key(name: str, value: str) -> str:
    if _is_placeholder(value):
        raise RuntimeError(
            f"Missing API key: {name} is not configured. "
            "Copy .env.example to .env and fill in the real key."
        )
    return value
