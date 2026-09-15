"""Business logic for pattern ratings: hashing, upsert/delete, admin queries."""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from drumgen.db.models import PatternRating
from drumgen.sticking_generator import GENERATOR_VERSION


def content_hash(pattern: dict[str, Any]) -> str:
    """Stable sha256 of a pattern's content, independent of dict key order."""
    canonical = json.dumps(pattern, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


async def upsert_rating(
    session: AsyncSession,
    *,
    rater_id: uuid.UUID,
    rating: int,
    tags: list[str],
    note: str | None,
    kind: str,
    pattern: dict[str, Any],
    params: dict[str, Any],
    seed: int | None,
) -> PatternRating:
    digest = content_hash(pattern)
    row = await session.scalar(
        select(PatternRating).where(
            PatternRating.rater_id == rater_id, PatternRating.content_hash == digest
        )
    )
    if row is None:
        row = PatternRating(rater_id=rater_id, content_hash=digest)
        session.add(row)
    row.rating = rating
    row.tags = tags
    row.note = note
    row.kind = kind
    row.pattern = pattern
    row.params = params
    row.seed = seed
    row.generator_version = GENERATOR_VERSION
    row.moderated_out = False
    row.moderated_by = None
    row.moderated_at = None
    await session.commit()
    await session.refresh(row)
    return row


async def delete_rating(
    session: AsyncSession, *, rater_id: uuid.UUID, pattern: dict[str, Any]
) -> None:
    row = await session.scalar(
        select(PatternRating).where(
            PatternRating.rater_id == rater_id,
            PatternRating.content_hash == content_hash(pattern),
        )
    )
    if row is not None:
        await session.delete(row)
        await session.commit()
