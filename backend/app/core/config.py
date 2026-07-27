from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")

    app_name: str = "AI Exam Quality Platform"
    app_env: str = "development"
    api_prefix: str = "/api/v1"
    secret_key: str = Field(default="development-only-change-me", min_length=16)
    # "localhost", not the Docker Compose service name "postgres": this is
    # the default for running the backend natively (matches upload_root/
    # kb_source_dir's existing native-friendly-default convention below).
    # docker-compose.yml overrides this back to the "postgres" hostname for
    # its own backend container via an explicit `environment:` entry, since
    # that hostname only resolves inside the Compose network.
    database_url: str = "postgresql+psycopg://exam_quality:exam_quality@localhost:5432/exam_quality"
    max_upload_mb: int = Field(default=50, ge=1, le=200)
    allowed_origins: str = "http://localhost:5173"
    upload_root: str = "../storage/uploads"
    kb_source_dir: str = "../knowledge_base/source"
    report_root: str = "../storage/reports"
    # "localhost"/8001: the host-published port for running natively (matches
    # database_url's native-friendly-default convention above).
    # docker-compose.yml overrides these to the "chromadb" Compose hostname
    # and its in-network port 8000.
    chroma_host: str = "localhost"
    chroma_port: int = 8001
    vector_store_provider: str = "memory"
    ai_provider: str = "local"
    ai_model: str = "local-governed-baseline-v1"
    ai_api_key: str = ""
    ai_validation_retries: int = Field(default=1, ge=0, le=2)

    # First-party faculty authentication. Access tokens are short-lived signed
    # bearer tokens; password reset tokens are random, hashed, single-use DB rows.
    auth_access_token_minutes: int = Field(default=720, ge=15, le=10080)
    auth_issuer: str = "ai-exam-quality-platform"
    auth_audience: str = "ai-exam-quality-web"
    password_reset_token_minutes: int = Field(default=30, ge=5, le=1440)
    password_reset_url: str = "http://localhost:5173/reset-password"
    smtp_host: str = ""
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    smtp_use_tls: bool = True

    @property
    def allowed_origin_list(self) -> list[str]:
        return [item.strip() for item in self.allowed_origins.split(",") if item.strip()]


def validate_runtime_settings(settings: Settings) -> None:
    """Fail closed when a pilot/production environment lacks auth essentials."""

    if settings.app_env.lower() not in {"staging", "production"}:
        return
    insecure_defaults = {
        "development-only-change-me",
        "replace-with-a-long-random-development-secret",
    }
    if settings.secret_key in insecure_defaults or len(settings.secret_key) < 32:
        raise RuntimeError("A strong SECRET_KEY is required outside development.")
    if not settings.smtp_host or not settings.smtp_from_email:
        raise RuntimeError("SMTP_HOST and SMTP_FROM_EMAIL are required for password reset.")


@lru_cache
def get_settings() -> Settings:
    return Settings()
