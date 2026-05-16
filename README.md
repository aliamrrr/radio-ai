# Next Radio 24/7

An AI-generated 24/7 radio station that runs fully autonomously. Every night a pipeline searches the web for current events, writes broadcast scripts with GPT, synthesises cover art with fal.ai, and converts scripts to speech with Gradium TTS. A Next.js web app serves the result — playback is wall-clock-synced so every listener hears the same thing at the same time, just like a real radio station.

---

## Features

- **Live sync** — playback position is locked to real time; late arrivals jump straight to the right offset
- **Music breaks** — dedicated slots with custom cover art and continuous audio
- **Replay mode** — listen to any past slot on demand
- **Script viewer** — read the full broadcast script for any show
- **Themed schedule** — colour-coded by thematique (news, tech, culture, lifestyle, sports)
- **HTTP range streaming** — smooth seeking without audio restarts
- **Nightly pipeline** — fully automated: search → script → image → TTS → programme.json

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                  Nightly Pipeline  (00:00)                │
│                                                          │
│  Orchestrator  (gpt-5-mini)                                  │
│    └─ generates targeted search queries per theme        │
│                                                          │
│  Theme Agents  (parallel)                                │
│    └─ Tavily web search → gpt-5-mini script writing          │
│         └─ writes sujet + script → programme.json        │
│                                                          │
│  Media Agent   (fal.ai flux/schnell)                     │
│    └─ AI cover art → media/images/{id}.png               │
│                                                          │
│  TTS Agent     (Gradium)                                 │
│    └─ mono / dialogue synthesis → media/audio/{id}.mp3   │
└──────────────────────────────────────────────────────────┘
                          │
                  programme.json
                 (single source of truth)
                          │
┌──────────────────────────────────────────────────────────┐
│                   Next.js Web App                         │
│                                                          │
│  GET /api/programme  → reads programme.json (5 s cache)  │
│  GET /api/media/...  → streams files with Range support  │
│                                                          │
│  NowOnAir   current slot, cover image, host names        │
│  Player     HTML5 audio synced to wall-clock offset      │
│  ComingUp   next 3 upcoming slots                        │
│  Schedule   full day — past / live / upcoming            │
└──────────────────────────────────────────────────────────┘
```

---

## Tech stack

| Layer | Technology |
|-------|-----------|
| Web frontend | Next.js 14 (App Router), React 18, Tailwind CSS |
| AI — scripts | OpenAI GPT (configurable model) |
| AI — images | fal.ai `flux/schnell` |
| AI — speech | Gradium TTS |
| Web search | Tavily |
| Pipeline | Python 3.11+, Pydantic, httpx, pydub |
| Scheduling | cron via `scripts/cron_install.sh` |

---

## Prerequisites

- **Python** 3.11+
- **Node.js** 18+ and npm
- **ffmpeg** (required by pydub for audio processing)
- API keys for OpenAI, Tavily, fal.ai, and Gradium

---

## Setup

```bash
# 1. Clone the repo
git clone https://github.com/aliamrrr/radio-ai.git
cd radio-ai

# 2. Run the setup script (creates venv, installs deps, scaffolds dirs)
./scripts/setup.sh

# 3. Configure environment variables
cp .env.example .env
# Edit .env and fill in your API keys (see Environment variables below)

# 4. Install web dependencies
cd web && npm install
```

---

## Running locally

### Dev mode (no API keys needed)

```bash
# Seed programme.json with mock data — no external calls
python -m pipeline.run_daily --seed-mock

# Start the web app
cd web && npm run dev
```

Open http://localhost:3000. The full UI works with example content so you can test live sync, replay, and the schedule without any API keys.

### Real run

```bash
# Full pipeline: web search + GPT scripts + cover images + TTS
python -m pipeline.run_daily

# Scripts only, skip media (faster, cheaper)
python -m pipeline.run_daily --dry-run

# Regenerate a single slot
python -m pipeline.run_daily --slot 1800_news
```

---

## Environment variables

Copy `.env.example` to `.env` and fill in:

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | GPT script generation and search query generation |
| `OPENAI_MODEL` | Model name (default: `gpt-4o-mini`) |
| `TAVILY_API_KEY` | Web search for current events |
| `FAL_API_KEY` | Cover image generation via fal.ai |
| `FAL_MODEL` | fal.ai model (default: `fal-ai/flux/schnell`) |
| `GRADIUM_API_KEY` | Gradium TTS for audio synthesis |
| `GRADIUM_BASE_URL` | Gradium API base URL |
| `VOICE_MAP` | `Name=voice_id` pairs, comma-separated |
| `TIMEZONE` | Broadcast timezone (default: `Europe/Paris`) |
| `PROGRAMME_PATH` | Path to programme.json (default: repo root) |
| `MEDIA_DIR` | Path to media output directory |

**Voice map example:**
```
VOICE_MAP=Claire=voice_fr_female_1,Marc=voice_fr_male_1,Léa=voice_fr_female_2
```

---

## Project structure

```
radio-ai/
├── pipeline/
│   ├── run_daily.py       # Entry point — orchestrates the full nightly run
│   ├── orchestrator.py    # Generates search queries per theme via GPT
│   ├── theme_agent.py     # Tavily search + GPT script writing per slot
│   ├── audio_producer.py  # Assembles final MP3 from TTS segments
│   ├── tts.py             # Gradium TTS client
│   ├── media_agent.py     # fal.ai image generation
│   ├── schema.py          # Pydantic models for programme.json
│   ├── config.py          # Env var loading and path resolution
│   └── utils.py           # Shared helpers
├── web/
│   ├── app/
│   │   ├── page.tsx                    # Main radio page
│   │   ├── layout.tsx                  # Root layout and metadata
│   │   └── api/
│   │       ├── programme/route.ts      # Serves programme.json
│   │       └── media/[...path]/route.ts# Streams media with Range support
│   ├── components/
│   │   ├── Player.tsx      # Audio player, wall-clock sync
│   │   ├── NowOnAir.tsx    # Current slot display
│   │   ├── Schedule.tsx    # Full day schedule
│   │   ├── ComingUp.tsx    # Upcoming slots
│   │   └── ScriptModal.tsx # Script reader modal
│   └── lib/
│       ├── schedule.ts     # Slot timing utilities (Paris TZ aware)
│       ├── types.ts        # TypeScript types
│       └── themes.ts       # Per-thematique colour tokens
├── media/
│   ├── audio/              # Generated MP3s (git-ignored)
│   ├── images/             # Generated cover art (git-ignored)
│   └── music/              # Static music break assets
├── scripts/
│   ├── setup.sh            # One-shot environment setup
│   └── cron_install.sh     # Installs midnight cron job
└── programme.json          # Live schedule and metadata
```

---

## Programme format

`programme.json` is the single source of truth. Static fields define the schedule; the pipeline fills in dynamic fields each night.

```jsonc
{
  "id": "1600_news",              // unique slot identifier
  "start_time": "16:00",          // HH:MM in the configured timezone
  "duration_sec": 300,            // slot length in seconds
  "thematique": "international news",
  "nb_intervenants": 1,
  "noms": ["Claire"],             // host names (must match VOICE_MAP keys)
  "langue": "fr",
  "type_script": "presentation",  // presentation|dialogue|story|debate|analysis|daily recap|music
  "sujet": null,                  // filled by pipeline
  "script": null,                 // filled by pipeline
  "image_path": null,             // filled by pipeline → media/images/{id}.png
  "audio_path": null,             // filled by pipeline → media/audio/{id}.mp3
  "last_generated_at": null
}
```

**Adding a slot:** append an entry with all dynamic fields set to `null`. The next nightly run generates the content.

**Adding a host:** add the name to `noms` and add `Name=voice_id` to the `VOICE_MAP` env var.

**Music breaks:** set `type_script` to `"music"` — the UI will display the music break cover and apply the purple theme. Place the corresponding audio file at `media/audio/{id}.mp3`.

---

## Nightly automation

```bash
# Install cron job (runs pipeline at 00:00 every day)
./scripts/cron_install.sh

# View installed cron entries
crontab -l
```

---

## Deployment notes

- The web app is a standard Next.js app and can be deployed to Vercel, a VPS, or any Node.js host.
- `media/` must be writable by the pipeline process and readable by the web server.
- The pipeline is designed to run on the same machine as the web server; point `PROGRAMME_PATH` and `MEDIA_DIR` at shared locations if they differ.
- The `/api/media/[...path]` route handles HTTP Range requests (`206 Partial Content`) so seeking works correctly without re-downloading the full file.

---

## Known limitations

- **Gradium TTS** — the client is isolated in `pipeline/tts.py`. Update `_call_gradium_tts_stub()` when official API docs are available.
- **fal.ai** — similarly isolated in `pipeline/media_agent.py`. Model name and response shape may need adjustment.
- **Single-day schedule** — the programme resets at midnight; multi-day archives are not implemented.
- **No live failover** — if a slot has no audio, the player shows a disabled state.
