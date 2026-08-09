"""Production/staging safety checks: validate_runtime_settings (the startup
guard for weak secrets and missing SMTP) and the interactive-API-docs
gating decision. Both are pure functions of a Settings/string value, so they
are tested directly rather than by spinning up a second app.main FastAPI
instance under different environment variables (app.main's `app` object -
and the get_settings() it is built from - is a module-level singleton
shared with every other test in this suite; re-importing it under different
settings would risk polluting that shared state for unrelated tests)."""

from __future__ import annotations

import pytest

from app.core.config import Settings, validate_runtime_settings
from app.main import docs_enabled_for


def _settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "secret_key": "a" * 32,
        "database_url": "sqlite:///:memory:",
        "smtp_host": "smtp.example.com",
        "smtp_from_email": "noreply@example.com",
    }
    values.update(overrides)
    return Settings(**values)  # type: ignore[arg-type]


class TestValidateRuntimeSettings:
    def test_development_is_never_checked(self) -> None:
        """The default/dev environment must never be blocked by production
        readiness checks - the real default Settings() (the known-insecure
        default key, no SMTP) is exactly what native development uses."""
        settings = _settings(
            app_env="development",
            secret_key="development-only-change-me",
            smtp_host="",
            smtp_from_email="",
        )
        validate_runtime_settings(settings)  # must not raise

    @pytest.mark.parametrize("app_env", ["staging", "production", "PRODUCTION", " Staging "])
    def test_weak_secret_key_is_rejected(self, app_env: str) -> None:
        # 20 characters: long enough to satisfy Settings.secret_key's own
        # Field(min_length=16), short enough to fail
        # validate_runtime_settings' stricter >=32 production/staging check.
        settings = _settings(app_env=app_env, secret_key="a-twenty-char-key!!!")
        with pytest.raises(RuntimeError, match="SECRET_KEY"):
            validate_runtime_settings(settings)

    @pytest.mark.parametrize(
        "insecure_default",
        [
            "development-only-change-me",
            "replace-with-a-long-random-development-secret",
        ],
    )
    def test_known_insecure_default_keys_are_rejected_even_if_long(
        self, insecure_default: str
    ) -> None:
        # Pad to 32+ chars so only the "known insecure default" branch, not
        # the length check, is what rejects it.
        settings = _settings(app_env="production", secret_key=insecure_default)
        with pytest.raises(RuntimeError, match="SECRET_KEY"):
            validate_runtime_settings(settings)

    @pytest.mark.parametrize("app_env", ["staging", "production"])
    def test_missing_smtp_host_is_rejected(self, app_env: str) -> None:
        settings = _settings(app_env=app_env, smtp_host="")
        with pytest.raises(RuntimeError, match="SMTP"):
            validate_runtime_settings(settings)

    @pytest.mark.parametrize("app_env", ["staging", "production"])
    def test_missing_smtp_from_email_is_rejected(self, app_env: str) -> None:
        settings = _settings(app_env=app_env, smtp_from_email="")
        with pytest.raises(RuntimeError, match="SMTP"):
            validate_runtime_settings(settings)

    @pytest.mark.parametrize("app_env", ["staging", "production"])
    def test_fully_configured_settings_pass(self, app_env: str) -> None:
        settings = _settings(app_env=app_env)
        validate_runtime_settings(settings)  # must not raise


class TestDocsEnabledFor:
    @pytest.mark.parametrize("app_env", ["development", "test", "dev", "", "local"])
    def test_docs_enabled_outside_staging_and_production(self, app_env: str) -> None:
        assert docs_enabled_for(app_env) is True

    @pytest.mark.parametrize(
        "app_env", ["staging", "production", "PRODUCTION", " Staging ", "Production"]
    )
    def test_docs_disabled_for_staging_and_production(self, app_env: str) -> None:
        assert docs_enabled_for(app_env) is False
