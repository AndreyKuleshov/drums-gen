"""Endpoints for liking / listing / removing saved patterns."""

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from drumgen.auth.deps import CurrentUser, SessionDep
from drumgen.db.models import LikedPattern
from drumgen.patterns.schemas import LikedOut, LikeIn

router = APIRouter(prefix="/patterns", tags=["patterns"])


@router.post("/like", response_model=LikedOut, status_code=status.HTTP_201_CREATED)
async def like_pattern(body: LikeIn, user: CurrentUser, session: SessionDep) -> LikedOut:
    row = LikedPattern(
        user_id=user.id,
        title=body.title,
        phrase=body.phrase.model_dump(mode="json"),
        meta=body.meta,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return LikedOut.from_row(row)


@router.get("/liked", response_model=list[LikedOut])
async def list_liked(user: CurrentUser, session: SessionDep) -> list[LikedOut]:
    rows = await session.scalars(
        select(LikedPattern)
        .where(LikedPattern.user_id == user.id)
        .order_by(LikedPattern.created_at.desc())
    )
    return [LikedOut.from_row(row) for row in rows]


@router.delete("/liked/{pattern_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unlike_pattern(pattern_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> None:
    row = await session.scalar(
        select(LikedPattern).where(LikedPattern.id == pattern_id, LikedPattern.user_id == user.id)
    )
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pattern not found")
    await session.delete(row)
    await session.commit()
