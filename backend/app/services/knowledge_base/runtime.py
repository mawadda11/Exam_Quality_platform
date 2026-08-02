"""Validated KB snapshot and process-local semantic runtime."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.core.config import Settings
from app.services.ai.factory import build_ai_provider
from app.services.ai.provider import AiProvider
from app.services.knowledge_base.embedding_text import build_embeddable_records
from app.services.knowledge_base.factory import build_vector_store
from app.services.knowledge_base.manifest import build_manifest
from app.services.knowledge_base.models import NormalizedRecord
from app.services.knowledge_base.normalizer import normalize_all
from app.services.knowledge_base.validator import load_and_validate
from app.services.knowledge_base.vector_store import EmbeddableRecord, VectorStore


@dataclass(frozen=True)
class KnowledgeBaseSnapshot:
    version: str
    aggregate_hash: str
    records: tuple[NormalizedRecord, ...]
    embeddable_records: tuple[EmbeddableRecord, ...]


class SemanticRuntime:
    def __init__(
        self,
        *,
        provider: AiProvider,
        vector_store: VectorStore,
        snapshot: KnowledgeBaseSnapshot,
    ) -> None:
        self.provider = provider
        self.vector_store = vector_store
        self.snapshot = snapshot
        self._indexed = False

    def ensure_index(self) -> None:
        if self._indexed:
            return
        self.rebuild_index()

    def rebuild_index(self) -> None:
        self.vector_store.replace_version(
            self.snapshot.embeddable_records,
            kb_version=self.snapshot.version,
        )
        self._indexed = True


def load_kb_snapshot(source_dir: Path) -> KnowledgeBaseSnapshot:
    raw = load_and_validate(source_dir)
    records = normalize_all(raw)
    manifest = build_manifest(source_dir, raw, records, "valid")
    version = str(manifest["version"])
    aggregate_hash = str(manifest["aggregate_record_hash"])
    embeddable = build_embeddable_records(
        records,
        kb_version=version,
        kb_hash=aggregate_hash,
    )
    return KnowledgeBaseSnapshot(
        version=version,
        aggregate_hash=aggregate_hash,
        records=tuple(records),
        embeddable_records=tuple(embeddable),
    )


@lru_cache(maxsize=16)
def _cached_runtime(
    app_env: str,
    kb_source_dir: str,
    vector_store_provider: str,
    chroma_host: str,
    chroma_port: int,
    ai_provider: str,
    ai_model: str,
    ai_api_key: str,
    gemini_api_key: str,
    ai_validation_retries: int,
) -> SemanticRuntime:
    settings = Settings(
        app_env=app_env,
        kb_source_dir=kb_source_dir,
        vector_store_provider=vector_store_provider,
        chroma_host=chroma_host,
        chroma_port=chroma_port,
        ai_provider=ai_provider,
        ai_model=ai_model,
        ai_api_key=ai_api_key,
        gemini_api_key=gemini_api_key,
        ai_validation_retries=ai_validation_retries,
    )
    return SemanticRuntime(
        provider=build_ai_provider(settings),
        vector_store=build_vector_store(settings),
        snapshot=load_kb_snapshot(Path(kb_source_dir).resolve()),
    )


def get_semantic_runtime(settings: Settings) -> SemanticRuntime:
    return _cached_runtime(
        settings.app_env,
        str(Path(settings.kb_source_dir).resolve()),
        settings.vector_store_provider,
        settings.chroma_host,
        settings.chroma_port,
        settings.ai_provider,
        settings.ai_model,
        settings.ai_api_key,
        settings.gemini_api_key.get_secret_value(),
        settings.ai_validation_retries,
    )


def clear_semantic_runtime_cache() -> None:
    """Test/support hook for configuration or controlled KB snapshot changes."""
    _cached_runtime.cache_clear()
