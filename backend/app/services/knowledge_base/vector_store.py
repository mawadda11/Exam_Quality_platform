"""Provider-neutral, KB-version-isolated semantic retrieval.

Exact-ID governance lookups remain in ``reference_data.py``. This module is
only for similarity retrieval of reviewed KB text. Every record preserves
its official source identity, record hash, KB version, and aggregate KB hash.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

_COLLECTION_NAME = "knowledge_base"


@dataclass(frozen=True)
class EmbeddableRecord:
    record_id: str
    official_id: str
    text: str
    entity_type: str
    dimension: str | None
    requirement_id: str | None
    rule_id: str | None
    provenance_category: str
    kb_version: str
    kb_hash: str
    source_workbook: str
    source_row_number: int
    record_hash: str


@dataclass(frozen=True)
class RetrievedRecord:
    record_id: str
    official_id: str
    text: str
    entity_type: str
    dimension: str | None
    requirement_id: str | None
    rule_id: str | None
    provenance_category: str
    kb_version: str
    kb_hash: str
    source_workbook: str
    source_row_number: int
    record_hash: str


class VectorStore(Protocol):
    def replace_version(self, records: Sequence[EmbeddableRecord], *, kb_version: str) -> None:
        """Atomically from the caller's perspective replaces one KB version.

        Implementations delete records for ``kb_version`` before upserting
        the supplied snapshot, preventing stale rows from surviving a rebuild.
        """
        ...

    def query(
        self,
        text: str,
        *,
        kb_version: str,
        entity_type: str | None = None,
        dimension: str | None = None,
        requirement_id: str | None = None,
        rule_id: str | None = None,
        n_results: int = 5,
    ) -> list[RetrievedRecord]:
        """Similarity search constrained to one explicit KB version."""
        ...


def _build_where(
    *,
    kb_version: str,
    entity_type: str | None,
    dimension: str | None,
    requirement_id: str | None,
    rule_id: str | None,
) -> dict[str, object]:
    clauses: list[dict[str, object]] = [{"kb_version": kb_version}]
    if entity_type is not None:
        clauses.append({"entity_type": entity_type})
    if dimension is not None:
        clauses.append({"dimension": dimension})
    if requirement_id is not None:
        clauses.append({"requirement_id": requirement_id})
    if rule_id is not None:
        clauses.append({"rule_id": rule_id})
    if len(clauses) == 1:
        return clauses[0]
    return {"$and": clauses}


def _metadata(record: EmbeddableRecord) -> dict[str, str | int]:
    return {
        "official_id": record.official_id,
        "entity_type": record.entity_type,
        "dimension": record.dimension or "",
        "requirement_id": record.requirement_id or "",
        "rule_id": record.rule_id or "",
        "provenance_category": record.provenance_category,
        "kb_version": record.kb_version,
        "kb_hash": record.kb_hash,
        "source_workbook": record.source_workbook,
        "source_row_number": record.source_row_number,
        "record_hash": record.record_hash,
    }


def _from_result(
    record_id: str, document: str | None, metadata: Mapping[str, object]
) -> RetrievedRecord:
    source_row_number = metadata.get("source_row_number", 0)
    return RetrievedRecord(
        record_id=record_id,
        official_id=str(metadata.get("official_id", "")),
        text=document or "",
        entity_type=str(metadata.get("entity_type", "")),
        dimension=str(metadata.get("dimension", "")) or None,
        requirement_id=str(metadata.get("requirement_id", "")) or None,
        rule_id=str(metadata.get("rule_id", "")) or None,
        provenance_category=str(metadata.get("provenance_category", "")),
        kb_version=str(metadata.get("kb_version", "")),
        kb_hash=str(metadata.get("kb_hash", "")),
        source_workbook=str(metadata.get("source_workbook", "")),
        source_row_number=(
            source_row_number if isinstance(source_row_number, int) else int(str(source_row_number))
        ),
        record_hash=str(metadata.get("record_hash", "")),
    )


def _build_chroma_http_client(*, host: str, port: int) -> Any:
    """Import the optional Chroma dependency only when it is selected."""

    try:
        import chromadb
    except ImportError as exc:  # pragma: no cover - exercised in deployment images
        raise RuntimeError(
            "The chromadb package is required when VECTOR_STORE_PROVIDER=chroma."
        ) from exc
    return chromadb.HttpClient(host=host, port=port)


class ChromaVectorStore:
    """HTTP-backed Chroma implementation using its bundled local embeddings."""

    def __init__(self, *, host: str, port: int) -> None:
        self._client = _build_chroma_http_client(host=host, port=port)
        self._collection = self._client.get_or_create_collection(_COLLECTION_NAME)

    def replace_version(self, records: Sequence[EmbeddableRecord], *, kb_version: str) -> None:
        self._collection.delete(where={"kb_version": kb_version})
        if not records:
            return
        self._collection.upsert(
            ids=[record.record_id for record in records],
            documents=[record.text for record in records],
            metadatas=[_metadata(record) for record in records],
        )

    def query(
        self,
        text: str,
        *,
        kb_version: str,
        entity_type: str | None = None,
        dimension: str | None = None,
        requirement_id: str | None = None,
        rule_id: str | None = None,
        n_results: int = 5,
    ) -> list[RetrievedRecord]:
        if n_results < 1:
            raise ValueError("n_results must be at least 1.")
        if self._collection.count() == 0:
            return []
        where = _build_where(
            kb_version=kb_version,
            entity_type=entity_type,
            dimension=dimension,
            requirement_id=requirement_id,
            rule_id=rule_id,
        )
        results = self._collection.query(
            query_texts=[text],
            n_results=n_results,
            where=where,
        )
        ids = results["ids"][0]
        documents = results["documents"][0] if results["documents"] else []
        metadatas = results["metadatas"][0] if results["metadatas"] else []
        return [
            _from_result(record_id, document, dict(metadata or {}))
            for record_id, document, metadata in zip(ids, documents, metadatas, strict=True)
        ]


_TOKEN = re.compile(r"[a-z0-9]+", re.IGNORECASE)


class InMemoryVectorStore:
    """Deterministic retrieval test double; never performs external I/O."""

    def __init__(self) -> None:
        self._records: dict[str, EmbeddableRecord] = {}

    def replace_version(self, records: Sequence[EmbeddableRecord], *, kb_version: str) -> None:
        self._records = {
            record_id: record
            for record_id, record in self._records.items()
            if record.kb_version != kb_version
        }
        self._records.update({record.record_id: record for record in records})

    def query(
        self,
        text: str,
        *,
        kb_version: str,
        entity_type: str | None = None,
        dimension: str | None = None,
        requirement_id: str | None = None,
        rule_id: str | None = None,
        n_results: int = 5,
    ) -> list[RetrievedRecord]:
        if n_results < 1:
            raise ValueError("n_results must be at least 1.")
        query_tokens = set(_TOKEN.findall(text.casefold()))
        ranked: list[tuple[int, EmbeddableRecord]] = []
        for record in self._records.values():
            if record.kb_version != kb_version:
                continue
            if entity_type is not None and record.entity_type != entity_type:
                continue
            if dimension is not None and record.dimension != dimension:
                continue
            if requirement_id is not None and record.requirement_id != requirement_id:
                continue
            if rule_id is not None and record.rule_id != rule_id:
                continue
            score = len(query_tokens & set(_TOKEN.findall(record.text.casefold())))
            if score > 0:
                ranked.append((score, record))
        ranked.sort(key=lambda item: (-item[0], item[1].record_id))
        return [
            _from_result(record.record_id, record.text, _metadata(record))
            for _, record in ranked[:n_results]
        ]
