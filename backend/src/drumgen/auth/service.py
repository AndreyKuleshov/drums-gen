"""Auth business logic: registration, verification, login sessions, reset.

All functions take an AsyncSession and commit their own unit of work. Email
enumeration is avoided at the API layer (register/forgot always look the same to
the caller); the branching here just decides what, if anything, to email.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from drumgen.auth.errors import (
    EmailNotVerifiedError,
    InvalidCredentialsError,
    InvalidTokenError,
)
from drumgen.auth.security import generate_token, hash_password, hash_token, verify_password
from drumgen.config import Settings
from drumgen.db.models import EmailToken, Session, User
from drumgen.mailer.templates import (
    send_already_registered_email,
    send_password_reset_email,
    send_verification_email,
)


def _now() -> datetime:
    return datetime.now(UTC)


async def register(
    session: AsyncSession,
    settings: Settings,
    *,
    email: str,
    password: str,
    display_name: str,
) -> None:
    email = email.strip().lower()
    existing = await session.scalar(select(User).where(User.email == email))
    if existing is not None:
        if existing.is_verified:
            await send_already_registered_email(settings, existing.email)
        else:
            await _issue_email_token(session, settings, existing, purpose="verify")
        return

    user = User(
        email=email,
        password_hash=hash_password(password),
        display_name=display_name,
    )
    session.add(user)
    await session.flush()
    await _issue_email_token(session, settings, user, purpose="verify")


async def _issue_email_token(
    session: AsyncSession, settings: Settings, user: User, *, purpose: str
) -> None:
    raw = generate_token()
    ttl_hours = (
        settings.verify_token_ttl_hours if purpose == "verify" else settings.reset_token_ttl_hours
    )
    session.add(
        EmailToken(
            user_id=user.id,
            token_hash=hash_token(raw),
            purpose=purpose,
            expires_at=_now() + timedelta(hours=ttl_hours),
        )
    )
    await session.commit()

    if purpose == "verify":
        link = f"{settings.public_base_url}/verify?token={raw}"
        await send_verification_email(settings, user.email, link)
    else:
        link = f"{settings.public_base_url}/reset?token={raw}"
        await send_password_reset_email(settings, user.email, link)


async def _consume_token(session: AsyncSession, raw: str, purpose: str) -> User:
    token = await session.scalar(
        select(EmailToken).where(
            EmailToken.token_hash == hash_token(raw), EmailToken.purpose == purpose
        )
    )
    if token is None or token.consumed_at is not None or token.expires_at < _now():
        raise InvalidTokenError
    user = await session.get(User, token.user_id)
    if user is None:
        raise InvalidTokenError
    token.consumed_at = _now()
    return user


async def verify_email(session: AsyncSession, raw_token: str) -> User:
    user = await _consume_token(session, raw_token, "verify")
    if user.email_verified_at is None:
        user.email_verified_at = _now()
    await session.commit()
    return user


async def authenticate(session: AsyncSession, *, email: str, password: str) -> User:
    email = email.strip().lower()
    user = await session.scalar(select(User).where(User.email == email))
    if (
        user is None
        or user.password_hash is None
        or not verify_password(password, user.password_hash)
    ):
        raise InvalidCredentialsError
    if user.email_verified_at is None:
        raise EmailNotVerifiedError
    return user


async def create_session(
    session: AsyncSession, settings: Settings, user: User, user_agent: str | None
) -> str:
    raw = generate_token()
    session.add(
        Session(
            user_id=user.id,
            token_hash=hash_token(raw),
            expires_at=_now() + timedelta(days=settings.session_ttl_days),
            user_agent=(user_agent or "")[:255] or None,
        )
    )
    await session.commit()
    return raw


async def user_for_session(session: AsyncSession, raw_token: str | None) -> User | None:
    if not raw_token:
        return None
    row = await session.scalar(select(Session).where(Session.token_hash == hash_token(raw_token)))
    if row is None or row.revoked_at is not None or row.expires_at < _now():
        return None
    return await session.get(User, row.user_id)


async def revoke_session(session: AsyncSession, raw_token: str) -> None:
    row = await session.scalar(select(Session).where(Session.token_hash == hash_token(raw_token)))
    if row is not None and row.revoked_at is None:
        row.revoked_at = _now()
        await session.commit()


async def request_password_reset(session: AsyncSession, settings: Settings, email: str) -> None:
    email = email.strip().lower()
    user = await session.scalar(select(User).where(User.email == email))
    if user is None:
        return
    await _issue_email_token(session, settings, user, purpose="reset")


async def reset_password(session: AsyncSession, raw_token: str, new_password: str) -> None:
    user = await _consume_token(session, raw_token, "reset")
    user.password_hash = hash_password(new_password)
    await session.commit()
