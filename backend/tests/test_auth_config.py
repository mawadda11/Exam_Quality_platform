from __future__ import annotations

import pytest

from app.core.config import Settings, validate_runtime_settings


def test_development_allows_local_auth_defaults() -> None:
    validate_runtime_settings(Settings(app_env="development"))


def test_production_rejects_default_secret() -> None:
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        validate_runtime_settings(
            Settings(
                app_env="production",
                smtp_host="smtp.example.org",
                smtp_from_email="no-reply@example.org",
            )
        )


def test_production_requires_password_reset_email_delivery() -> None:
    with pytest.raises(RuntimeError, match="SMTP_HOST"):
        validate_runtime_settings(
            Settings(
                app_env="production",
                secret_key="a-production-secret-that-is-long-enough-2026",
            )
        )
