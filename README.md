# AI Radio 24/7

An AI-generated 24/7 radio station. Every night, a pipeline fetches today's news via web search, writes scripts with GPT-4o, generates cover images with fal.ai, and synthesizes audio with Gradium TTS. A Next.js web app serves the content, auto-syncing playback to wall-clock time.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Nightly Pipeline (00:00)              │
│                                                         │
│  Orchestrator (GPT-4o)                                  │
│    └─ generates search queries per theme                │
│                                                         │
│  Theme Agents (parallel)                                │
│    └─ Tavily web search → GPT-4o script writing         │
│         └─ writes sujet + script to programme.json      │
│                                                         │
│  Media Agent (fal.ai)                                   │
│    └─ generates cover art → media/images/{id}.png       │
│                                                         │
│  TTS Agent (Gradium)                                    │
│    └─ mono/dialogue synthesis → media/audio/{id}.mp3    │
└─────────────────────────────────────────────────────────┘
                           │
                   programme.json
                  (source of truth)
                           │
┌─────────────────────────────────────────────────────────┐
│                  Next.js Web App                        │
│                                                         │
│  GET /api/programme  ─── reads programme.json (5s cache)│
│  GET /api/media/...  ─── streams from /media/           │
│                                                         │
│  page.tsx                                               │
│   ├─ NowOnAir — current slot, cover, hosts              │
│   ├─ Player   — HTML5 audio, synced to wall clock       │
│   ├─ ComingUp — next 3 slots                            │
│   └─ Schedule — full day, past/current/upcoming         │
└─────────────────────────────────────────────────────────┘
```

---

## Setup

```bash
# 1. Clone and run setup
./scripts/setup.sh

# 2. Fill in your API keys
cp .env.example .env
# Edit .env with real values for:
#   OPENAI_API_KEY, TAVILY_API_KEY, GRADIUM_API_KEY, FAL_API_KEY
```

---

## First run (offline / dev mode)

```bash
# Populate programme.json with mock data — no API calls
python -m pipeline.run_daily --seed-mock

# Start the UI
cd web && npm run dev
```

The app will be at http://localhost:3000. The schedule is seeded with example content so you can test the full UI without any API keys.

---

## Real run (requires API keys)

```bash
# Full pipeline: search + scripts + images + TTS
python -m pipeline.run_daily

# Dry run: only scripts, no media (cheaper)
python -m pipeline.run_daily --dry-run

# Regenerate a single slot
python -m pipeline.run_daily --slot 0710_tech
```

---

## Schedule — `programme.json`

`programme.json` is the source of truth. Static fields define the schedule; dynamic fields are filled by the pipeline.

| Slot ID       | Time  | Theme             | Hosts           | Format       |
|---------------|-------|-------------------|-----------------|--------------|
| 0700_news     | 07:00 | International news| Claire          | Presentation |
| 0710_tech     | 07:10 | Tech & AI         | Marc + Léa      | Dialogue     |
| 0720_culture  | 07:20 | Culture           | Sofia           | Story        |
| 1200_news     | 12:00 | International news| Claire          | Presentation |
| 1210_lifestyle| 12:10 | Lifestyle         | Tom + Inès      | Dialogue     |
| 1800_news     | 18:00 | International news| Claire          | Presentation |
| 1810_tech     | 18:10 | Tech & AI         | Marc            | Presentation |
| 1820_culture  | 18:20 | Culture           | Sofia + Hugo    | Debate       |

### Adding a new slot

Add an entry to `programme.json` with all static fields set and all dynamic fields as `null`. The next pipeline run will generate content for it.

### Adding a new host

1. Add the host's name to `noms` in their slot.
2. Add a voice mapping to `VOICE_MAP` in `.env`:
   ```
   VOICE_MAP=...,NewHost=voice_id_from_gradium
   ```

---

## Cron (automatic nightly run)

```bash
./scripts/cron_install.sh
```

This installs a `crontab` entry that runs the pipeline at midnight every day.

---

## Known limitations

- **Gradium TTS** — the API endpoint and request shape are stubs pending official docs. The client is isolated in `pipeline/tts.py:_call_gradium_tts_stub()`. When docs are available, update that function only.
- **fal.ai** — similarly stubbed in `pipeline/media_agent.py:_call_fal_stub()`. The model name and response shape may need adjustment.
- **No music between slots** — gaps in the schedule show "Off air". Background music is a planned feature.
- **Single-day looping** — the schedule resets at midnight. Multi-day archives are not yet implemented.
- **Silent audio stub** — if Gradium is not configured, the pipeline generates a silent MP3 of the correct duration so the UI can test playback end-to-end.

---

## What needs real API keys before going live

| Service       | Key env var        | Feature blocked |
|---------------|--------------------|-----------------|
| OpenAI        | `OPENAI_API_KEY`   | Script generation, search query generation |
| Tavily        | `TAVILY_API_KEY`   | Web search for current events |
| fal.ai        | `FAL_API_KEY`      | Cover image generation |
| Gradium TTS   | `GRADIUM_API_KEY`  | Audio synthesis |
