from email.message import EmailMessage

from pytest import MonkeyPatch

from app.core.config import Settings
from app.core.domain import LanguageCode
from app.services.auth.email import send_password_reset_email


class _SmtpCapture:
    messages: list[EmailMessage] = []

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        pass

    def __enter__(self) -> "_SmtpCapture":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def starttls(self) -> None:
        pass

    def login(self, _username: str, _password: str) -> None:
        pass

    def send_message(self, message: EmailMessage) -> None:
        self.messages.append(message)


def test_password_reset_email_uses_account_language_and_approved_brand(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.services.auth.email.smtplib.SMTP", _SmtpCapture)
    _SmtpCapture.messages.clear()
    settings = Settings(
        smtp_host="smtp.example.test",
        smtp_from_email="noreply@example.test",
        smtp_use_tls=False,
    )

    assert send_password_reset_email(
        settings=settings,
        recipient="arabic@example.test",
        token="arabic-token",
        language=LanguageCode.ARABIC,
    )
    assert send_password_reset_email(
        settings=settings,
        recipient="english@example.test",
        token="english-token",
        language=LanguageCode.ENGLISH,
    )

    assert _SmtpCapture.messages[0]["Subject"] == ("إعادة تعيين كلمة مرور محلل جودة الاختبارات")
    assert _SmtpCapture.messages[1]["Subject"] == ("Reset your Exam Quality Analyzer password")
    payload = "\n".join(message.get_content() for message in _SmtpCapture.messages)
    assert "AI Exam Quality Platform" not in payload
    assert "Artificial Intelligence" not in payload
