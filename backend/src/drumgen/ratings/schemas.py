"""Request/response models for pattern ratings."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

RatingTag = Literal[
    "too_busy",
    "boring",
    "unmusical",
    "awkward_sticking",
    "repetitive",
    "too_hard",
    "groovy",
    "creative",
    "playable",
]


class RateIn(BaseModel):
    rating: Literal[-1, 0, 1]
    tags: list[RatingTag] = Field(default_factory=list[RatingTag])
    note: str | None = Field(default=None, max_length=500)
    kind: Literal["exercise", "pattern"]
    pattern: dict[str, Any]
    params: dict[str, Any]
    seed: int | None = None


class RatingOut(BaseModel):
    id: uuid.UUID
    rating: int
    tags: list[str]
    note: str | None
    created_at: datetime
