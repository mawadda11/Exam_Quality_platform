from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.analyses import router as analyses_router
from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.api.reports import router as reports_router
from app.core.config import get_settings, validate_runtime_settings
from app.core.errors import register_exception_handlers


def docs_enabled_for(app_env: str) -> bool:
    """Interactive API docs are a development/test convenience, not
    something the public internet should reach - staging/production
    terminate at a reverse proxy with no other consumer of this API, so
    /docs, /redoc, and the raw OpenAPI schema are disabled outside
    development."""
    return app_env.strip().casefold() not in {"staging", "production"}


settings = get_settings()
validate_runtime_settings(settings)
_docs_enabled = docs_enabled_for(settings.app_env)
app = FastAPI(
    title=settings.app_name,
    version="2.0.0-rc1",
    docs_url="/docs" if _docs_enabled else None,
    redoc_url="/redoc" if _docs_enabled else None,
    openapi_url="/openapi.json" if _docs_enabled else None,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(health_router, prefix=settings.api_prefix)
app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(analyses_router, prefix=settings.api_prefix)
app.include_router(reports_router, prefix=settings.api_prefix)
register_exception_handlers(app)
