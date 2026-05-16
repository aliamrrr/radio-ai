from __future__ import annotations

from datetime import datetime
from typing import Any, Optional, Union

from pydantic import BaseModel, field_validator


class Slot(BaseModel):
    id: str
    start_time: str
    duration_sec: Union[int, str] = 0
    thematique: str
    nb_intervenants: int = 0
    noms: list[str] = []
    langue: str = "fr"
    type_script: str

    sujet: Optional[str] = None
    script: Optional[str] = None
    image_path: Optional[str] = None
    audio_path: Optional[str] = None

    intro_audio_path: Optional[str] = None
    outro_audio_path: Optional[str] = None
    intro_image_path: Optional[str] = None
    outro_image_path: Optional[str] = None
    intro_duration_sec: Optional[int] = None
    outro_duration_sec: Optional[int] = None

    title: Optional[str] = None
    last_generated_at: Optional[Any] = None

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
