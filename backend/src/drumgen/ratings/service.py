"""Business logic for pattern ratings: hashing, upsert/delete, admin queries."""

from __future__ import annotations

import hashlib
import json
import uuid
from collections import Counter
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func as safunc
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from drumgen.db.models import PatternRating, User
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


async def list_ratings(
    session: AsyncSession,
    *,
    limit: int,
    offset: int,
    rating: int | None,
    tag: str | None,
    include_moderated: bool,
) -> tuple[list[tuple[PatternRating, str]], int]:
    stmt = select(PatternRating, User.email).join(User, PatternRating.rater_id == User.id)
    if not include_moderated:
        stmt = stmt.where(PatternRating.moderated_out.is_(False))
    if rating is not None:
        stmt = stmt.where(PatternRating.rating == rating)
    if tag is not None:
        stmt = stmt.where(PatternRating.tags.contains([tag]))
    total = await session.scalar(select(safunc.count()).select_from(stmt.subquery())) or 0
    rows = await session.execute(
        stmt.order_by(PatternRating.created_at.desc()).limit(limit).offset(offset)
    )
    return [(r[0], r[1]) for r in rows.all()], total


async def summarize(session: AsyncSession) -> dict[str, Any]:
    rows = await session.scalars(
        select(PatternRating).where(PatternRating.moderated_out.is_(False))
    )
    likes = dislikes = 0
    dislike_tags: Counter[str] = Counter()
    for row in rows:
        if row.rating > 0:
            likes += 1
        elif row.rating < 0:
            dislikes += 1
            dislike_tags.update(row.tags)
    return {
        "total": likes + dislikes,
        "likes": likes,
        "dislikes": dislikes,
        "top_dislike_tags": [{"tag": t, "count": c} for t, c in dislike_tags.most_common(10)],
    }


async def moderate(
    session: AsyncSession, *, rating_id: uuid.UUID, moderator_id: uuid.UUID, moderated_out: bool
) -> tuple[PatternRating, str] | None:
    row = await session.scalar(select(PatternRating).where(PatternRating.id == rating_id))
    if row is None:
        return None
    row.moderated_out = moderated_out
    row.moderated_by = moderator_id if moderated_out else None
    row.moderated_at = datetime.now(UTC) if moderated_out else None
    await session.commit()
    email = await session.scalar(select(User.email).where(User.id == row.rater_id))
    return row, email or ""
