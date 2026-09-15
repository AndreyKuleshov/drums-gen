"""Pattern rating capture (users) + admin review/moderation."""

from fastapi import APIRouter, Response, status

from drumgen.auth.deps import CurrentUser, SessionDep
from drumgen.ratings import service
from drumgen.ratings.schemas import RateIn, RatingOut

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
