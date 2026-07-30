from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from urllib.parse import urlencode

from app.core.config import Settings
from app.core.domain import LanguageCode

logger = logging.getLogger(__name__)


def build_password_reset_url(settings: Settings, token: str) -> str:
    separator = "&" if "?" in settings.password_reset_url else "?"
    return f"{settings.password_reset_url}{separator}{urlencode({'token': token})}"


def send_password_reset_email(
    *,
    settings: Settings,
    recipient: str,
    token: str,
    language: LanguageCode = LanguageCode.ARABIC,
) -> bool:
    """Send a reset link without exposing the token to logs.

    Development/test callers receive a debug token from the API response instead.
    Production must configure SMTP; a delivery failure is logged using safe metadata
    only and the public endpoint still returns its generic anti-enumeration response.
    """

    if not settings.smtp_host or not settings.smtp_from_email:
        logger.warning("Password reset email skipped because SMTP is not configured.")
        return False

    message = EmailMessage()
    reset_url = build_password_reset_url(settings, token)
    if language is LanguageCode.ARABIC:
        message["Subject"] = "إعادة تعيين كلمة مرور محلل جودة الاختبارات"
        body = (
            "طُلبت إعادة تعيين كلمة المرور لحسابك في محلل جودة الاختبارات.\n\n"
            f"افتح الرابط التالي لاختيار كلمة مرور جديدة:\n{reset_url}\n\n"
            f"تنتهي صلاحية الرابط خلال {settings.password_reset_token_minutes} دقيقة. "
            "إذا لم تطلب إعادة التعيين، يمكنك تجاهل هذه الرسالة."
        )
    else:
        message["Subject"] = "Reset your Exam Quality Analyzer password"
        body = (
            "A password reset was requested for your Exam Quality Analyzer account.\n\n"
            f"Open this link to choose a new password:\n{reset_url}\n\n"
            f"This link expires in {settings.password_reset_token_minutes} minutes. "
            "If you did not request this reset, you can ignore this message."
        )
    message["From"] = settings.smtp_from_email
    message["To"] = recipient
    message.set_content(body)

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
