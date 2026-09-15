"""Request/response models for the auth endpoints."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, EmailStr, Field

from drumgen.db.models import User


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=80)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class VerifyIn(BaseModel):
    token: str = Field(min_length=1)


class ForgotIn(BaseModel):
    email: EmailStr


class ResetIn(BaseModel):
    token: str = Field(min_length=1)
    password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    id: uuid.UUID
    email: str  # output only — no need to re-validate as EmailStr
    display_name: str
    bio: str
    avatar_url: str | None
    social_links: list[str]
    is_verified: bool
    is_admin: bool

    @classmethod
    def from_user(cls, user: User) -> UserOut:
        avatar_url = f"/api/media/avatars/{user.avatar_path}" if user.avatar_path else None
        return cls(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            bio=user.bio,
            avatar_url=avatar_url,
            social_links=user.social_links,
            is_verified=user.is_verified,
            is_admin=user.is_admin,
        )
