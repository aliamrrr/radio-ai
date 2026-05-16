from __future__ import annotations

import json
import logging
import os
import shutil
from pathlib import Path

from rich.logging import RichHandler

from pipeline import config


def get_logger(name: str) -> logging.Logger:
    config.LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_file = config.LOGS_DIR / "pipeline.log"

    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )

    rich_handler = RichHandler(rich_tracebacks=True, markup=True)
    rich_handler.setLevel(logging.INFO)

    logger.addHandler(file_handler)
    logger.addHandler(rich_handler)
    return logger


def atomic_write_json(path: Path, data: object) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    shutil.move(str(tmp), str(path))


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_dirs() -> None:
    for d in [config.IMAGES_DIR, config.AUDIO_DIR, config.LOGS_DIR]:
        d.mkdir(parents=True, exist_ok=True)
