"""Pattern rating capture (users) + admin review/moderation."""

import uuid

from fastapi import APIRouter, HTTPException, Query, Response, status

from drumgen.auth.deps import AdminUser, CurrentUser, SessionDep
from drumgen.db.models import PatternRating
from drumgen.ratings import service
from drumgen.ratings.schemas import (
    AdminRatingOut,
    AdminRatingsPage,
    ModerateIn,
    RateIn,
    RatingOut,
    RatingSummary,
)

router = APIRouter(tags=["ratings"])


@router.post("/patterns2/rate", response_model=None)
async def rate_pattern(
    body: RateIn, user: CurrentUser, session: SessionDep
) -> RatingOut | Response:
    if body.rating == 0:
        await service.delete_rating(session, rater_id=user.id, pattern=body.pattern)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    row = await service.upsert_rating(
        session,
        rater_id=user.id,
        rating=body.rating,
        tags=list(body.tags),
        note=body.note,
        kind=body.kind,
        pattern=body.pattern,
        params=body.params,
        seed=body.seed,
    )
    return RatingOut(
        id=row.id, rating=row.rating, tags=row.tags, note=row.note, created_at=row.created_at
    )


def _admin_out(row: PatternRating, email: str) -> AdminRatingOut:
    return AdminRatingOut(
        id=row.id,
        rating=row.rating,
        tags=row.tags,
        note=row.note,
        kind=row.kind,
        pattern=row.pattern,
        params=row.params,
        generator_version=row.generator_version,
        seed=row.seed,
        rater_email=email,
        created_at=row.created_at,
        moderated_out=row.moderated_out,
    )


@router.get("/admin/ratings")
async def admin_list_ratings(
    admin: AdminUser,
    session: SessionDep,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    rating: int | None = Query(default=None),
    tag: str | None = Query(default=None),
    include_moderated: bool = Query(default=False),
) -> AdminRatingsPage:
    items, total = await service.list_ratings(
        session,
        limit=limit,
        offset=offset,
        rating=rating,
        tag=tag,
        include_moderated=include_moderated,
    )
    summary = await service.summarize(session)
    return AdminRatingsPage(
        items=[_admin_out(row, email) for row, email in items],
        total=total,
        summary=RatingSummary.model_validate(summary),
    )


@router.patch("/admin/ratings/{rating_id}")
async def admin_moderate_rating(
    rating_id: uuid.UUID, body: ModerateIn, admin: AdminUser, session: SessionDep
) -> AdminRatingOut:
    result = await service.moderate(
        session, rating_id=rating_id, moderator_id=admin.id, moderated_out=body.moderated_out
    )
    if result is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Rating not found")
    row, email = result
    return _admin_out(row, email)
