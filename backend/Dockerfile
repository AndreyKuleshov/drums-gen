# Drum Pattern Generator — API (FastAPI + uv)
FROM python:3.12-slim

# uv (fast Python package manager)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Install dependencies + the package (production only) into /app/.venv.
COPY pyproject.toml uv.lock ./
COPY src ./src
RUN uv sync --frozen --no-dev

# Run uvicorn straight from the venv (no runtime re-sync/rebuild).
ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
CMD ["uvicorn", "drumgen.api:app", "--host", "0.0.0.0", "--port", "8000"]
