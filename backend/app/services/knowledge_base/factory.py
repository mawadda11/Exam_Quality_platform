"""Settings-based vector-store construction."""

from __future__ import annotations

from app.core.config import Settings
from app.services.knowledge_base.vector_store import (
    ChromaVectorStore,
    InMemoryVectorStore,
    VectorStore,
)


class VectorStoreConfigurationError(RuntimeError):
    """Invalid vector-store configuration is an infrastructure failure."""


def build_vector_store(settings: Settings) -> VectorStore:
    provider = settings.vector_store_provider.strip().casefold()
    if provider == "memory":
        if settings.app_env.strip().casefold() == "production":
            raise VectorStoreConfigurationError(
                "The in-memory vector store is not permitted in production."
            )
        return InMemoryVectorStore()
    if provider == "chroma":
        if not settings.chroma_host.strip() or settings.chroma_port < 1:
            raise VectorStoreConfigurationError("Chroma host and port must be configured.")
        return ChromaVectorStore(host=settings.chroma_host, port=settings.chroma_port)
    raise VectorStoreConfigurationError(
        f"Unsupported VECTOR_STORE_PROVIDER: {settings.vector_store_provider!r}."
    )
