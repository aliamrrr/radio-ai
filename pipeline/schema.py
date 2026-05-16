from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, field_validator


ScriptType = Literal["presentation", "dialogue", "story", "debate"]
LanguageCode = Literal["fr", "en"]


class Slot(BaseModel):
    # Static fields
    id: str
    start_time: str  # "HH:MM" in Europe/Paris
    duration_sec: int
    thematique: str
    nb_intervenants: int
    noms: list[str]
    langue: LanguageCode
    type_script: ScriptType

    # Dynamic fields
    sujet: Optional[str] = None
    script: Optional[str] = None
    image_path: Optional[str] = None
    audio_path: Optional[str] = None
    last_generated_at: Optional[datetime] = None

    @field_validator("noms")
    @classmethod
    def noms_length_matches(cls, v: list[str], info) -> list[str]:
        data = info.data
        if "nb_intervenants" in data and len(v) != data["nb_intervenants"]:
            raise ValueError(
                f"noms length {len(v)} != nb_intervenants {data['nb_intervenants']}"
            )
        return v


Programme = list[Slot]
