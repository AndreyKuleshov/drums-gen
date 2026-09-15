"""ORM models for auth and accounts.

All tables live in the `drumgen` schema (via Base.metadata). Tokens are stored
as SHA-256 hashes, never in clear text. The schema is intentionally OAuth-ready
(`auth_identities`) even though only email/password ships first.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from drumgen.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Null for OAuth-only accounts (once social login lands).
    password_hash: Mapped[str | None] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(80))
    bio: Mapped[str] = mapped_column(Text, default="")
    avatar_path: Mapped[str | None] = mapped_column(String(255))
    # Social profile links (Instagram, YouTube, …), shown as brand icons.
    social_links: Mapped[list[str]] = mapped_column(
        JSONB, default=list, server_default="[]", nullable=False
    )
    is_admin: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    identities: Mapped[list[AuthIdentity]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    @property
    def is_verified(self) -> bool:
        return self.email_verified_at is not None


class AuthIdentity(Base):
    """A federated (OAuth) identity linked to a user. Unused until social login."""

    __tablename__ = "auth_identities"
    __table_args__ = (UniqueConstraint("provider", "provider_subject"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    provider: Mapped[str] = mapped_column(String(32))  # "google" | "apple"
    provider_subject: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship(back_populates="identities")


class EmailToken(Base):
    """One-time, hashed token for email verification and password reset."""

    __tablename__ = "email_tokens"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    purpose: Mapped[str] = mapped_column(String(16))  # "verify" | "reset"
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PasswordHistory(Base):
    """Past password hashes, so a reset can't reuse a recent one."""

    __tablename__ = "password_history"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class Session(Base):
    """An opaque, server-side session; the cookie carries only the raw token."""

    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    user_agent: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LikedPattern(Base):
    """A saved (liked) pattern. The full serialized Phrase is stored as JSONB so
    the favorite is self-contained and reproducible even as the generator
    evolves; `meta` holds the small display summary (meter/feel/bars/tempo)."""

    __tablename__ = "liked_patterns"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str | None] = mapped_column(String(120))
    phrase: Mapped[dict[str, Any]] = mapped_column(JSONB)
    meta: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class PatternRating(Base):
    """A user's like/dislike of a generated pattern, plus reason tags. The full
    pattern JSON is stored as ground truth for a training dataset; params + seed
    + generator_version make each row reproducible. Upsert key is
    (rater_id, content_hash); moderation is a soft-delete via `moderated_out`."""

    __tablename__ = "pattern_ratings"
    __table_args__ = (UniqueConstraint("rater_id", "content_hash"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    rater_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    rating: Mapped[int] = mapped_column(SmallInteger)  # +1 like, -1 dislike
    tags: Mapped[list[str]] = mapped_column(
        JSONB, default=list, server_default="[]", nullable=False
    )
    note: Mapped[str | None] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(String(16))  # "exercise" | "pattern"
    pattern: Mapped[dict[str, Any]] = mapped_column(JSONB)
    params: Mapped[dict[str, Any]] = mapped_column(JSONB)
    seed: Mapped[int | None] = mapped_column(BigInteger)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    generator_version: Mapped[str] = mapped_column(String(32))
    moderated_out: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    moderated_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    moderated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
