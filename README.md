# Drum Pattern Generator

Generates valid snare-drum rudiment patterns, renders them as notation, and plays them back.

## Quick start

    make install
    make dev            # backend :8000 + frontend :5173

If port 8000 is taken, pick another — the frontend follows automatically:

    make dev BACKEND_PORT=8010

The frontend reads the API base from `VITE_API_BASE` (default `http://localhost:8000`).

## Backend

    cd backend
    uv sync
    uv run pytest
    uv run uvicorn drumgen.api:app --reload --port 8000

## Frontend

    cd frontend
    npm install
    npm run dev   # http://localhost:5173

## Quality gates

- Backend: `uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run pytest`
- Frontend: `npm run typecheck && npm run test && npm run build`

See `docs/superpowers/specs/2026-07-29-drum-pattern-generator-design.md` for the design.
