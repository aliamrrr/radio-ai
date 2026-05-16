"""Quick script to regenerate only images, preserving existing scripts and audio."""
from __future__ import annotations

import ssl as _ssl
import urllib3 as _urllib3
_ssl._create_default_https_context = _ssl._create_unverified_context
_urllib3.disable_warnings(_urllib3.exceptions.InsecureRequestWarning)
import requests as _req
_orig = _req.adapters.HTTPAdapter.send
def _no_ssl(self, request, **kwargs): kwargs['verify'] = False; return _orig(self, request, **kwargs)
_req.adapters.HTTPAdapter.send = _no_ssl
import httpx as _httpx
_orig_init = _httpx.Client.__init__
def _patched(self, *a, **kw): kw.setdefault('verify', False); _orig_init(self, *a, **kw)
_httpx.Client.__init__ = _patched

import json
from pathlib import Path
from pipeline import config, media_agent
from pipeline.schema import Slot
from pipeline.utils import atomic_write_json, ensure_dirs, get_logger, load_json
from rich.console import Console

logger = get_logger(__name__)
console = Console()


def main():
    ensure_dirs()
    data = load_json(config.PROGRAMME_PATH)
    slots = [Slot.model_validate(s) for s in data]
    slot_map = {s.id: s for s in slots}

    console.print(f"[bold]Regenerating images for {len(slots)} slots...[/bold]")

    for slot in slots:
        img_path = config.IMAGES_DIR / f"{slot.id}.png"
        if img_path.exists():
            console.print(f"  [dim]{slot.id} already has image, skipping[/dim]")
            continue
        try:
            updated = media_agent.generate_image(slot)
            slot_map[slot.id] = updated
            console.print(f"  [green]{slot.id} image saved[/green]")
        except Exception as e:
            logger.error(f"  {slot.id} image failed: {e}")

    slots = list(slot_map.values())
    atomic_write_json(config.PROGRAMME_PATH, [s.model_dump(mode="json") for s in slots])
    console.print("[bold green]Done.[/bold green]")


if __name__ == "__main__":
    main()
