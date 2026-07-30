# Drum Pattern Generator

Generate valid snare-drum rudiment patterns of a chosen meter and length, render
them as notation, and play them back in the browser — cross-platform, no OS
audio engine required.

A deterministic backtracking generator guarantees legal sticking (never `rR`,
never three of the same hand in a row) while drawing varied rudiments from a
catalog of single/double strokes, paradiddles and rolls.

## Quick start

    make install
    make dev            # backend :8000 + frontend :5173

If port 8000 is taken, pick another — the frontend follows automatically:

    make dev BACKEND_PORT=8010

The frontend reads the API base from `VITE_API_BASE` (default
`http://localhost:8000`).

## Features

- **Meter, length, subdivision** controls (2/4…7/8, N bars, 1/8 or 1/16).
- **Feel:** Straight · Triplet · Mixed (varied note values per beat) · Authentic
  (rudiments play their internal rhythm — a roll's release note is longer).
- **Accents:** by rudiment, by metric beat, or both.
- **Notation** via VexFlow: sticking under each note, accents, beaming grouped by
  rudiment phrase, triplet tuplets, bars wrapped across systems.
- **Playback** via Tone.js: live tempo (changes without regenerating), loop,
  note highlighting synced to audio, distinct accent vs normal snare voices.
- **Metronome:** overlay a click on the pattern, or run a standalone practice
  metronome with selectable subdivision (1/4, 1/8, 1/16, + triplet) and accents
  on the beats.

## Layout

    backend/    Python API — Pydantic domain, rudiment catalog, generator, FastAPI
    frontend/   Vue 3 + Vite + TypeScript — VexFlow notation, Tone.js audio

## Backend

    cd backend
    uv sync
    uv run pytest
    uv run uvicorn drumgen.api:app --reload --port 8000

Endpoints: `POST /generate`, `GET /rudiments`.

## Frontend

    cd frontend
    npm install
    npm run dev   # http://localhost:5173

## Quality gates

    make check    # lint + typecheck + tests, both stacks

- Backend: `uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run pytest`
- Frontend: `npm run typecheck && npm run test && npm run build`

### Headless UI smoke (optional)

Playwright drives the app in Chromium and writes screenshots:

    cd frontend
    npm i -D playwright && npx playwright install chromium
    SHOOT_OUT=/tmp/shots node scripts/shoot.mjs
