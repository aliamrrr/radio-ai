from __future__ import annotations

import json
import logging
import shutil
from logging.handlers import RotatingFileHandler
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

    file_handler = RotatingFileHandler(
        log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
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


def atomic_write_json_and_upload(path: Path, data: object) -> None:
    """Write JSON locally then upload to R2 if configured."""
    atomic_write_json(path, data)

    from pipeline import storage  # deferred to avoid circular import at module load
    if storage.is_configured():
        try:
            storage.upload_file(path, "programme.json")
        except Exception as exc:
            get_logger(__name__).error(f"Failed to upload programme.json to R2: {exc}", exc_info=True)


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_dirs() -> None:
    for d in [config.IMAGES_DIR, config.AUDIO_DIR, config.LOGS_DIR]:
        d.mkdir(parents=True, exist_ok=True)
