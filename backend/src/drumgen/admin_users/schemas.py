"""Request/response models for admin user management."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from drumgen.db.models import User


class AdminUserOut(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str
    is_admin: bool
    is_verified: bool
    is_blocked: bool
    blocked_at: datetime | None
    created_at: datetime

    @classmethod
    def from_user(cls, user: User) -> AdminUserOut:
        return cls(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            is_admin=user.is_admin,
            is_verified=user.is_verified,
            is_blocked=user.is_blocked,
            blocked_at=user.blocked_at,
            created_at=user.created_at,
        )


class SetAdminIn(BaseModel):
    is_admin: bool


class SetBlockedIn(BaseModel):
    is_blocked: bool
