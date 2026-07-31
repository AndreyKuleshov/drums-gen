"""Generic SMTP sender (Brevo in prod, console in dev).

Provider-agnostic: any SMTP relay works via env config. When email is disabled
(local dev), messages are logged instead of sent so flows are testable offline.
"""

import logging
from email.message import EmailMessage

import aiosmtplib

from drumgen.config import Settings

logger = logging.getLogger("drumgen.mailer")


async def send_email(
    settings: Settings,
    *,
    to: str,
    subject: str,
    text: str,
    html: str | None = None,
) -> None:
    if not settings.email_enabled:
        logger.info("[email:dev] to=%s subject=%s\n%s", to, subject, text)
        if settings.email_debug_file:
            with open(settings.email_debug_file, "a", encoding="utf-8") as fh:
                fh.write(f"TO: {to}\nSUBJECT: {subject}\n{text}\n---\n")
        return

    message = EmailMessage()
    message["From"] = f"{settings.email_from_name} <{settings.email_from}>"
    message["To"] = to
    message["Subject"] = subject
    message.set_content(text)
    if html is not None:
        message.add_alternative(html, subtype="html")

    await aiosmtplib.send(
        message,
        hostname=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_user or None,
        password=settings.smtp_password or None,
        start_tls=settings.smtp_starttls,
    )
