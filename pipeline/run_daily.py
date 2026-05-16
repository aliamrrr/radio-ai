from __future__ import annotations

# ── Global SSL bypass for corporate proxy that intercepts TLS ──────────────────
import ssl as _ssl
import urllib3 as _urllib3

# Disable certificate verification at the ssl module level
_ssl._create_default_https_context = _ssl._create_unverified_context

# Suppress InsecureRequestWarning from urllib3
_urllib3.disable_warnings(_urllib3.exceptions.InsecureRequestWarning)

# Patch requests.HTTPAdapter so every request skips SSL verification
import requests as _requests_mod
_orig_adapter_send = _requests_mod.adapters.HTTPAdapter.send
def _patched_adapter_send(self, request, **kwargs):
    kwargs['verify'] = False
    return _orig_adapter_send(self, request, **kwargs)
_requests_mod.adapters.HTTPAdapter.send = _patched_adapter_send

# Patch httpx.Client and httpx.AsyncClient to disable SSL verification globally
import httpx as _httpx
_orig_httpx_client_init = _httpx.Client.__init__
def _patched_httpx_client_init(self, *args, **kwargs):
    kwargs.setdefault('verify', False)
    _orig_httpx_client_init(self, *args, **kwargs)
_httpx.Client.__init__ = _patched_httpx_client_init

_orig_httpx_async_init = _httpx.AsyncClient.__init__
def _patched_httpx_async_init(self, *args, **kwargs):
    kwargs.setdefault('verify', False)
    _orig_httpx_async_init(self, *args, **kwargs)
_httpx.AsyncClient.__init__ = _patched_httpx_async_init

import argparse
import asyncio
import json
import shutil
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from rich.console import Console
from rich.table import Table

from pipeline import audio_producer, config
from pipeline import media_agent, tts
from pipeline.orchestrator import generate_queries
from pipeline.schema import Slot
from pipeline.theme_agent import process_theme
from pipeline.utils import atomic_write_json, ensure_dirs, get_logger, load_json

logger = get_logger(__name__)
console = Console()


def load_programme() -> list[Slot]:
    data = load_json(config.PROGRAMME_PATH)
    return [Slot.model_validate(s) for s in data]


def save_programme(slots: list[Slot]) -> None:
    data = [s.model_dump(mode="json") for s in slots]
    atomic_write_json(config.PROGRAMME_PATH, data)


def seed_mock(slots: list[Slot]) -> list[Slot]:
    example_path = config.PROGRAMME_PATH.parent / "programme.example.json"
    if not example_path.exists():
        console.print("[red]programme.example.json not found.[/red]")
        return slots
    example = load_json(example_path)
    example_map = {s["id"]: s for s in example}
    updated = []
    for slot in slots:
        ex = example_map.get(slot.id)
        if ex:
            slot = slot.model_copy(
                update={
                    "sujet": ex.get("sujet"),
                    "script": ex.get("script"),
                    "image_path": ex.get("image_path"),
                    "audio_path": ex.get("audio_path"),
                    "last_generated_at": datetime.now(timezone.utc),
                }
            )
        updated.append(slot)
    return updated


def run_pipeline(slots: list[Slot], dry_run: bool = False, skip_tts: bool = False) -> list[Slot]:
    # Step 1: Generate search queries via orchestrator
    console.print("[bold cyan]Step 1/5:[/bold cyan] Generating search queries...")
    queries_by_theme = generate_queries(slots)

    # Step 2: Run theme agents in parallel
    console.print("[bold cyan]Step 2/5:[/bold cyan] Running theme agents...")
    themes = list({s.thematique for s in slots})

    with ThreadPoolExecutor(max_workers=max(len(themes), 1)) as pool:
        futures = {
            theme: pool.submit(
                process_theme,
                theme,
                queries_by_theme.get(theme, []),
                slots,
            )
            for theme in themes
        }
        theme_results: dict[str, list[Slot]] = {}
        for theme, future in futures.items():
            try:
                theme_results[theme] = future.result()
            except Exception as e:
                logger.error(f"Theme agent crashed for '{theme}': {e} — keeping original slots")
                theme_results[theme] = [s for s in slots if s.thematique == theme]

    # Merge: last theme's update for each slot wins
    slot_map: dict[str, Slot] = {s.id: s for s in slots}
    for theme, updated_slots in theme_results.items():
        for s in updated_slots:
            if s.thematique == theme:
                slot_map[s.id] = s
    slots = list(slot_map.values())

    if dry_run:
        console.print("[bold green]Dry run complete. Scripts generated:[/bold green]")
        _print_scripts(slots)
        return slots

    # Step 3: Generate images in parallel
    console.print("[bold cyan]Step 3/5:[/bold cyan] Generating images...")
    with ThreadPoolExecutor(max_workers=4) as pool:
        image_futures = {s.id: pool.submit(media_agent.generate_image, s) for s in slots}
        for slot_id, future in image_futures.items():
            try:
                updated = future.result()
                slot_map[slot_id] = updated
            except Exception as e:
                logger.error(f"Image generation failed for {slot_id}: {e}")
    slots = list(slot_map.values())

    # Step 4: Synthesize audio in parallel
    if skip_tts:
        console.print("[bold yellow]Step 4/5:[/bold yellow] Skipping TTS (--skip-tts).")
    else:
        console.print("[bold cyan]Step 4/5:[/bold cyan] Synthesizing audio...")
        with ThreadPoolExecutor(max_workers=2) as pool:
            tts_futures = {s.id: pool.submit(tts.synthesize_slot, s) for s in slots}
            for slot_id, future in tts_futures.items():
                try:
                    updated = future.result()
                    slot_map[slot_id] = updated
                except Exception as e:
                    logger.error(f"TTS failed for {slot_id}: {e}")
    slots = list(slot_map.values())

    # Step 4.5: Merge intros/outros, auto-detect and fill gaps with music
    console.print("[bold cyan]Step 4.5/5:[/bold cyan] Producing final audio (intro+script+outro, auto gap fills)...")
    slots = audio_producer.process_all_audio(list(slot_map.values()))
    slot_map = {s.id: s for s in slots}

    # Step 5: Stamp timestamps and save
    console.print("[bold cyan]Step 5/5:[/bold cyan] Saving programme.json...")
    now = datetime.now(timezone.utc)
    slots = [s.model_copy(update={"last_generated_at": now}) for s in slots]
    save_programme(slots)

    return slots


def run_single_slot(slot_id: str, slots: list[Slot], dry_run: bool = False) -> list[Slot]:
    slot = next((s for s in slots if s.id == slot_id), None)
    if slot is None:
        raise ValueError(f"Slot '{slot_id}' not found in programme.json")

    queries_by_theme = generate_queries([slot])
    updated = process_theme(
        slot.thematique,
        queries_by_theme.get(slot.thematique, []),
        [slot],
    )
    slot = next(s for s in updated if s.id == slot_id)

    if dry_run:
        console.print(f"[bold green]Slot {slot_id} script:[/bold green]\n{slot.script}")
        slot_map = {s.id: s for s in slots}
        slot_map[slot_id] = slot
        return list(slot_map.values())

    slot = media_agent.generate_image(slot)
    slot = tts.synthesize_slot(slot)
    slot = audio_producer.merge_show_audio(slot)
    slot = slot.model_copy(update={"last_generated_at": datetime.now(timezone.utc)})

    slot_map = {s.id: s for s in slots}
    slot_map[slot_id] = slot
    slots = list(slot_map.values())
    save_programme(slots)
    return slots


def _print_scripts(slots: list[Slot]) -> None:
    table = Table(title="Generated Scripts", show_lines=True)
    table.add_column("Slot ID", style="cyan")
    table.add_column("Sujet")
    table.add_column("Script (preview)")
    for s in slots:
        preview = (s.script or "")[:120] + "..." if s.script else "[dim]null[/dim]"
        table.add_row(s.id, s.sujet or "[dim]null[/dim]", preview)
    console.print(table)


def main() -> None:
    parser = argparse.ArgumentParser(description="AI Radio — nightly pipeline")
    parser.add_argument("--slot", help="Regenerate a single slot by ID")
    parser.add_argument("--dry-run", action="store_true", help="Generate scripts only, no media/TTS")
    parser.add_argument("--skip-tts", action="store_true", help="Skip audio synthesis (scripts + images only)")
    parser.add_argument("--seed-mock", action="store_true", help="Seed programme.json with mock data")
    parser.add_argument("--reset-schedule", action="store_true", help="Reset programme.json from programme.exemple.json template")
    args = parser.parse_args()

    ensure_dirs()

    if args.reset_schedule:
        src = config.RADIO_ASSETS_DIR / "programme.exemple.json"
        if src.exists():
            import shutil
            shutil.copy(src, config.PROGRAMME_PATH)
            console.print(f"[green]Schedule reset from {src}[/green]")
        else:
            console.print(f"[red]Template not found: {src}[/red]")
        return

    slots = load_programme()
    console.print(f"[bold]AI Radio Pipeline[/bold] — {len(slots)} slots loaded")

    if args.seed_mock:
        console.print("[yellow]Seeding mock data from programme.example.json...[/yellow]")
        slots = seed_mock(slots)
        save_programme(slots)
        console.print("[green]Mock data seeded. Run 'cd web && npm run dev' to start the UI.[/green]")
        return

    if args.slot:
        slots = run_single_slot(args.slot, slots, dry_run=args.dry_run)
    else:
        slots = run_pipeline(slots, dry_run=args.dry_run, skip_tts=args.skip_tts)

    console.print("[bold green]Pipeline complete.[/bold green]")


if __name__ == "__main__":
    main()
