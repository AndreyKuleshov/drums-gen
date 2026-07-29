# Drum Pattern Generator

Generates valid snare-drum rudiment patterns, renders them as notation, and plays them back.

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
