"""FastAPI dependencies for reading the current authenticated user."""

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from drumgen.auth import service
from drumgen.config import Settings, get_settings
from drumgen.db.engine import get_session
from drumgen.db.models import User

SessionDep = Annotated[AsyncSession, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


async def current_user(request: Request, session: SessionDep, settings: SettingsDep) -> User:
    raw = request.cookies.get(settings.cookie_name)
    user = await service.user_for_session(session, raw)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    return user


CurrentUser = Annotated[User, Depends(current_user)]


async def admin_user(user: CurrentUser) -> User:
    if not user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin only")
    return user


AdminUser = Annotated[User, Depends(admin_user)]
