"""Admin-only user management: list users, grant/revoke admin."""

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from drumgen.admin_users.schemas import AdminUserOut, SetAdminIn, SetBlockedIn
from drumgen.auth import service
from drumgen.auth.deps import AdminUser, SessionDep
from drumgen.db.models import User

router = APIRouter(prefix="/admin/users", tags=["admin-users"])


@router.get("")
async def list_users(admin: AdminUser, session: SessionDep) -> list[AdminUserOut]:
    rows = await session.scalars(select(User).order_by(User.created_at.desc()))
    return [AdminUserOut.from_user(u) for u in rows]


@router.patch("/{user_id}")
async def set_user_admin(
    user_id: uuid.UUID, body: SetAdminIn, admin: AdminUser, session: SessionDep
) -> AdminUserOut:
    if user_id == admin.id and not body.is_admin:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You can't revoke your own admin rights")
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    user.is_admin = body.is_admin
    await session.commit()
    await session.refresh(user)
    return AdminUserOut.from_user(user)


@router.patch("/{user_id}/block")
async def set_user_blocked(
    user_id: uuid.UUID, body: SetBlockedIn, admin: AdminUser, session: SessionDep
) -> AdminUserOut:
    if user_id == admin.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You can't block yourself")
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    await service.set_blocked(session, user, blocked=body.is_blocked)
    await session.refresh(user)
    return AdminUserOut.from_user(user)
