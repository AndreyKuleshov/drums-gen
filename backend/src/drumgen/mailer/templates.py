"""Plain, dependency-free email bodies for the auth flows."""

from drumgen.config import Settings
from drumgen.mailer import client

_APP = "Rudiment Engine"


async def send_verification_email(settings: Settings, to: str, link: str) -> None:
    text = (
        f"Welcome to {_APP}!\n\n"
        f"Confirm your email address to activate your account:\n{link}\n\n"
        f"This link expires in {settings.verify_token_ttl_hours} hours. "
        f"If you didn't sign up, you can ignore this message."
    )
    await client.send_email(settings, to=to, subject=f"Confirm your {_APP} account", text=text)


async def send_password_reset_email(settings: Settings, to: str, link: str) -> None:
    text = (
        f"We received a request to reset your {_APP} password.\n\n"
        f"Set a new password:\n{link}\n\n"
        f"This link expires in {settings.reset_token_ttl_hours} hours. "
        f"If you didn't ask for this, you can safely ignore this message."
    )
    await client.send_email(settings, to=to, subject=f"Reset your {_APP} password", text=text)


async def send_already_registered_email(settings: Settings, to: str) -> None:
    text = (
        f"Someone tried to register a {_APP} account with this email, but you "
        f"already have one. If it was you, just sign in — no action needed."
    )
    await client.send_email(
        settings, to=to, subject=f"You already have a {_APP} account", text=text
    )
