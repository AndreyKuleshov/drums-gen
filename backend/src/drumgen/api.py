from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from drumgen.catalog import MVP_CATALOG
from drumgen.domain.models import Phrase
from drumgen.generator import GenerateRequest, GenerationError, generate

app = FastAPI(title="Drum Pattern Generator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(GenerationError)
async def generation_error_handler(_request: Request, exc: GenerationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.post("/generate", response_model=Phrase)
def post_generate(req: GenerateRequest) -> Phrase:
    return generate(req)


@app.get("/rudiments")
def get_rudiments() -> list[dict[str, object]]:
    return [{"id": t.id, "name": t.name, "length_cells": t.length_cells} for t in MVP_CATALOG]
