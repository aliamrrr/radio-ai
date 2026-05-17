from __future__ import annotations

import re
from datetime import datetime
from typing import Optional, Union

from pydantic import BaseModel, Field, field_validator

_SAFE_ID = re.compile(r'^[a-zA-Z0-9_\-]+$')
_VALID_TIME = re.compile(r'^\d{2}:\d{2}$')

VALID_SCRIPT_TYPES = frozenset({
    "presentation", "dialogue", "story", "debate",
    "analysis", "daily recap", "music",
})
VALID_LANGS = frozenset({"fr", "en", "es", "de", "it", "pt"})


class Slot(BaseModel):
    id: str = Field(..., max_length=50)
    start_time: str = Field(..., max_length=5)
    duration_sec: Union[int, str] = 0
    thematique: str = Field(..., max_length=100)
    nb_intervenants: int = Field(0, ge=0, le=10)
    noms: list[str] = Field(default_factory=list)
    langue: str = Field("fr", max_length=10)
    type_script: str = Field(..., max_length=50)

    sujet: Optional[str] = Field(None, max_length=500)
    script: Optional[str] = Field(None, max_length=50_000)
    image_path: Optional[str] = Field(None, max_length=2000)
    audio_path: Optional[str] = Field(None, max_length=500)

    intro_audio_path: Optional[str] = Field(None, max_length=500)
    outro_audio_path: Optional[str] = Field(None, max_length=500)
    intro_image_path: Optional[str] = Field(None, max_length=500)
    outro_image_path: Optional[str] = Field(None, max_length=500)
    intro_duration_sec: Optional[int] = None
    outro_duration_sec: Optional[int] = None

    title: Optional[str] = Field(None, max_length=200)
    last_generated_at: Optional[datetime] = None

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        if not _SAFE_ID.match(v):
            raise ValueError(f"id contains invalid characters: {v!r}")
        return v

    @field_validator("start_time")
    @classmethod
    def validate_start_time(cls, v: str) -> str:
        if not _VALID_TIME.match(v):
            raise ValueError(f"start_time must be HH:MM, got: {v!r}")
        h, m = int(v[:2]), int(v[3:])
        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise ValueError(f"start_time out of range: {v!r}")
        return v

    @field_validator("type_script")
    @classmethod
    def validate_type_script(cls, v: str) -> str:
        if v not in VALID_SCRIPT_TYPES:
            raise ValueError(f"type_script {v!r} not in allowed set {VALID_SCRIPT_TYPES}")
        return v

    @field_validator("noms", mode="before")
    @classmethod
    def validate_noms(cls, v: list) -> list:
        items = v or []
        if len(items) > 10:
            raise ValueError("noms must have at most 10 entries")
        return [str(n)[:50] for n in items]

    @field_validator("duration_sec", mode="before")
    @classmethod
    def parse_duration(cls, v):
        if isinstance(v, str) and v.startswith("PLACEHOLDER"):
            return 0
        try:
            return int(v)
        except (ValueError, TypeError):
            return 0

    @field_validator("sujet", "script", "image_path", "audio_path",
                     "intro_image_path", "outro_image_path", mode="before")
    @classmethod
    def clear_placeholders(cls, v):
        if isinstance(v, str) and v.startswith("PLACEHOLDER"):
            return None
        return v

    @field_validator("intro_duration_sec", "outro_duration_sec", mode="before")
    @classmethod
    def parse_opt_duration(cls, v):
        if v is None or (isinstance(v, str) and v.startswith("PLACEHOLDER")):
            return None
        try:
            return int(v)
        except (ValueError, TypeError):
            return None

    @property
    def is_music(self) -> bool:
        return self.type_script == "music"

    @property
    def duration_int(self) -> int:
        return self.duration_sec if isinstance(self.duration_sec, int) else 0

    def start_seconds(self) -> int:
        h, m = self.start_time.split(":")
        return int(h) * 3600 + int(m) * 60


Programme = list[Slot]
