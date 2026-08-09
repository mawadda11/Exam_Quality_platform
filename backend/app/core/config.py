from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")

    app_name: str = "Exam Quality Analyzer"
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
    exam_ocr_provider: str = "tesseract"
    exam_ocr_fallback_enabled: bool = True
    extraction_ai_enabled: bool = False
    extraction_ai_provider: str = "gemini"
    extraction_ai_model: str = "gemini-3.6-flash"
    extraction_ai_validation_retries: int = Field(default=1, ge=0, le=2)
    extraction_ai_page_dpi: int = Field(default=144, ge=96, le=200)
    extraction_ai_max_pages_per_document: int = Field(default=25, ge=1, le=100)
    extraction_ai_cache_enabled: bool = True
    extraction_ai_targeted_ocr_enabled: bool = True
    extraction_ai_candidate_min_confidence: float = Field(default=0.55, ge=0, le=1)
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
    # Fully local optional adapter: no credential, just a reachable Ollama
    # server. Native default targets the host's own Ollama; docker-compose.yml
    # overrides this to host.docker.internal so the backend container can
    # reach an Ollama instance running on the host, without publishing Ollama
    # itself on any public network interface.
    ollama_base_url: str = "http://localhost:11434"
    ollama_timeout_seconds: int = Field(default=60, ge=1, le=300)
    # SecretStr (not plain str): never rendered by repr()/str()/logging of a
    # Settings instance - an extra guard against accidental exposure on top
    # of the existing rule that no provider ever logs its credential.
    # Optional adapter, gated only by AI_PROVIDER=gemini (see
    # app.services.ai.factory) - blank by default, like ai_api_key.
    gemini_api_key: SecretStr = SecretStr("")
    ai_validation_retries: int = Field(default=1, ge=0, le=2)
    # Sticky per-analysis failover: every new analysis starts on AI_MODEL.
    # Availability failures downgrade that analysis only to GEMINI_FALLBACK_MODEL,
    # then to the governed local baseline. A later analysis starts from primary again.
    ai_failover_enabled: bool = True
    gemini_fallback_model: str = "gemini-3.5-flash-lite"
    ai_local_fallback_model: str = "local-governed-baseline-v1"

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

    if settings.exam_ocr_provider.strip().casefold() != "tesseract":
        raise RuntimeError("EXAM_OCR_PROVIDER must be 'tesseract' in this release.")
    if settings.extraction_ai_enabled:
        if settings.extraction_ai_provider.strip().casefold() != "gemini":
            raise RuntimeError("EXTRACTION_AI_PROVIDER must be 'gemini' when enabled.")
        if not settings.gemini_api_key.get_secret_value().strip():
            raise RuntimeError("GEMINI_API_KEY is required when extraction AI is enabled.")
    if (
        settings.ai_failover_enabled
        and (
            settings.extraction_ai_provider.strip().casefold() == "gemini"
            or settings.ai_provider.strip().casefold() == "gemini"
        )
        and not settings.gemini_fallback_model.strip()
    ):
        raise RuntimeError("GEMINI_FALLBACK_MODEL is required when AI failover is enabled.")

    if settings.app_env.strip().casefold() not in {"staging", "production"}:
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
