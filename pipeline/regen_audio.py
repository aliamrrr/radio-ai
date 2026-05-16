"""Regenerate audio for slots that have silent stubs or missing audio."""
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

from pipeline import config, tts
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

    console.print(f"[bold]Regenerating audio for {len(slots)} slots...[/bold]")

    for slot in slots:
        if not slot.script:
            console.print(f"  [dim]{slot.id} has no script, skipping[/dim]")
            continue
        try:
            updated = tts.synthesize_slot(slot)
            slot_map[slot.id] = updated
            console.print(f"  [green]{slot.id} audio saved[/green]")
        except Exception as e:
            logger.error(f"  {slot.id} audio failed: {e}")

    slots = list(slot_map.values())
    atomic_write_json(config.PROGRAMME_PATH, [s.model_dump(mode="json") for s in slots])
    console.print("[bold green]Done.[/bold green]")


if __name__ == "__main__":
    main()
