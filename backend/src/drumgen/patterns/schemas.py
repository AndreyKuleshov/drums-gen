"""Request/response models for liked patterns."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from drumgen.db.models import LikedPattern
from drumgen.domain.models import Phrase


class LikeIn(BaseModel):
    phrase: Phrase
    meta: dict[str, Any] = Field(default_factory=dict)
    title: str | None = Field(default=None, max_length=120)


class LikedOut(BaseModel):
    id: uuid.UUID
    title: str | None
    phrase: dict[str, Any]
    meta: dict[str, Any]
    created_at: datetime

    @classmethod
    def from_row(cls, row: LikedPattern) -> LikedOut:
        return cls(
            id=row.id,
            title=row.title,
            phrase=row.phrase,
            meta=row.meta,
            created_at=row.created_at,
        )
