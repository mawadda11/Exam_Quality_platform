from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from urllib.parse import urlencode

from app.core.config import Settings

logger = logging.getLogger(__name__)


def build_password_reset_url(settings: Settings, token: str) -> str:
    separator = "&" if "?" in settings.password_reset_url else "?"
    return f"{settings.password_reset_url}{separator}{urlencode({'token': token})}"


def send_password_reset_email(*, settings: Settings, recipient: str, token: str) -> bool:
    """Send a reset link without exposing the token to logs.

    Development/test callers receive a debug token from the API response instead.
    Production must configure SMTP; a delivery failure is logged using safe metadata
    only and the public endpoint still returns its generic anti-enumeration response.
    """

    if not settings.smtp_host or not settings.smtp_from_email:
        logger.warning("Password reset email skipped because SMTP is not configured.")
        return False

    message = EmailMessage()
    message["Subject"] = f"Reset your {settings.app_name} password"
    message["From"] = settings.smtp_from_email
    message["To"] = recipient
    message.set_content(
        "A password reset was requested for your account.\n\n"
        f"Open this link to choose a new password:\n{build_password_reset_url(settings, token)}\n\n"
        f"This link expires in {settings.password_reset_token_minutes} minutes. "
        "If you did not request this reset, you can ignore this message."
    )

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
            if settings.smtp_use_tls:
                server.starttls()
            if settings.smtp_username:
                server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(message)
        return True
    except (OSError, smtplib.SMTPException):
        logger.exception("Password reset email delivery failed.")
        return False
