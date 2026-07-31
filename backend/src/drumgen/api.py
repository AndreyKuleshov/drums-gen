from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from drumgen.account.router import router as account_router
from drumgen.auth.router import router as auth_router
from drumgen.catalog import MVP_CATALOG
from drumgen.config import get_settings
from drumgen.db.engine import engine
from drumgen.domain.models import Phrase
from drumgen.generator import GenerateRequest, GenerationError, generate
from drumgen.patterns.router import router as patterns_router


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    yield
    await engine.dispose()


app = FastAPI(title="Drum Pattern Generator", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    # Any localhost port (dev servers vary): 5173, 5180, etc. Credentials are
    # allowed so the session cookie flows when the SPA calls cross-origin in dev.
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(account_router)
app.include_router(patterns_router)

# Serve uploaded avatars from the media volume. The directory is created up front
# so the mount doesn't fail on a fresh deploy with an empty volume.
_media_dir = Path(get_settings().media_dir)
(_media_dir / "avatars").mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=_media_dir), name="media")


@app.exception_handler(GenerationError)
async def generation_error_handler(_request: Request, exc: GenerationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.post("/generate", response_model=Phrase)
def post_generate(req: GenerateRequest) -> Phrase:
    return generate(req)


_FILLER_RUDIMENTS = frozenset({"single", "double"})


@app.get("/rudiments")
def get_rudiments() -> list[dict[str, object]]:
    """The rudiment catalog used to build patterns, with sticking and ornaments."""
    return [
        {
            "id": t.id,
            "name": t.name,
            "difficulty": t.difficulty.value,
            "length": t.length_cells,
            "filler": t.id in _FILLER_RUDIMENTS,
            "sticking": [e.hand.value for e in t.elements],
            "accents": [e.accent for e in t.elements],
            "grace": [e.grace for e in t.elements],
        }
        for t in MVP_CATALOG
    ]
