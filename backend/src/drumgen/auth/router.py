"""HTTP endpoints for email/password auth + session cookies."""

from fastapi import APIRouter, HTTPException, Request, Response, status

from drumgen.auth import service
from drumgen.auth.deps import CurrentUser, SessionDep, SettingsDep
from drumgen.auth.errors import (
    EmailNotVerifiedError,
    InvalidCredentialsError,
    InvalidTokenError,
)
from drumgen.auth.schemas import ForgotIn, LoginIn, RegisterIn, ResetIn, UserOut, VerifyIn
from drumgen.config import Settings

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_session_cookie(response: Response, settings: Settings, token: str) -> None:
    response.set_cookie(
        settings.cookie_name,
        token,
        max_age=settings.session_ttl_days * 86_400,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


@router.post("/register", status_code=status.HTTP_202_ACCEPTED)
async def register(body: RegisterIn, session: SessionDep, settings: SettingsDep) -> dict[str, str]:
    await service.register(
        session,
        settings,
        email=str(body.email),
        password=body.password,
        display_name=body.display_name,
    )
    return {"status": "verification_sent"}


@router.post("/verify")
async def verify(
    body: VerifyIn, response: Response, session: SessionDep, settings: SettingsDep
) -> UserOut:
    try:
        user = await service.verify_email(session, body.token)
    except InvalidTokenError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired token") from None
    token = await service.create_session(session, settings, user, None)
    _set_session_cookie(response, settings, token)
    return UserOut.from_user(user)


@router.post("/login")
async def login(
    body: LoginIn,
    request: Request,
    response: Response,
    session: SessionDep,
    settings: SettingsDep,
) -> UserOut:
    try:
        user = await service.authenticate(session, email=str(body.email), password=body.password)
    except EmailNotVerifiedError:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Email not verified") from None
    except InvalidCredentialsError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password") from None
    token = await service.create_session(session, settings, user, request.headers.get("user-agent"))
    _set_session_cookie(response, settings, token)
    return UserOut.from_user(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request, response: Response, session: SessionDep, settings: SettingsDep
) -> None:
    raw = request.cookies.get(settings.cookie_name)
    if raw:
        await service.revoke_session(session, raw)
    response.delete_cookie(settings.cookie_name, path="/")


@router.get("/me")
async def me(user: CurrentUser) -> UserOut:
    return UserOut.from_user(user)


@router.post("/forgot", status_code=status.HTTP_202_ACCEPTED)
async def forgot(body: ForgotIn, session: SessionDep, settings: SettingsDep) -> dict[str, str]:
    await service.request_password_reset(session, settings, str(body.email))
    return {"status": "reset_sent"}


@router.post("/reset")
async def reset(body: ResetIn, session: SessionDep) -> dict[str, str]:
    try:
        await service.reset_password(session, body.token, body.password)
    except InvalidTokenError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired token") from None
    return {"status": "password_reset"}
