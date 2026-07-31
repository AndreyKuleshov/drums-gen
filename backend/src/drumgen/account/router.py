"""Account profile endpoints: edit name/bio, upload avatar."""

from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from drumgen.account.avatars import AvatarError, process_avatar, remove_avatar
from drumgen.account.schemas import ProfileIn
from drumgen.auth.deps import CurrentUser, SessionDep, SettingsDep
from drumgen.auth.schemas import UserOut

router = APIRouter(prefix="/account", tags=["account"])


@router.patch("", response_model=UserOut)
async def update_profile(body: ProfileIn, user: CurrentUser, session: SessionDep) -> UserOut:
    user.display_name = body.display_name
    user.bio = body.bio
    await session.commit()
    return UserOut.from_user(user)


@router.post("/avatar", response_model=UserOut)
async def upload_avatar(
    user: CurrentUser,
    session: SessionDep,
    settings: SettingsDep,
    file: Annotated[UploadFile, File()],
) -> UserOut:
    raw = await file.read()
    if len(raw) > settings.avatar_max_bytes:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Image is too large (max 5MB)"
        )
    try:
        name = process_avatar(raw, settings.media_dir)
    except AvatarError:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Please upload a valid image (JPEG, PNG, or WebP)"
        ) from None

    old = user.avatar_path
    user.avatar_path = name
    await session.commit()
    if old:
        remove_avatar(old, settings.media_dir)
    return UserOut.from_user(user)
