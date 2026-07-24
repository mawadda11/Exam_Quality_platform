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

    @property
    def allowed_origin_list(self) -> list[str]:
        return [item.strip() for item in self.allowed_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
