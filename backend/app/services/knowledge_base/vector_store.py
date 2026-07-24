"""Vector-store adapter: a provider-neutral interface (docs/ARCHITECTURE.md's
"ChromaDB: replaceable vector retrieval implementation" and "External
providers hidden behind interfaces for testing and replacement") over the
already-provisioned ChromaDB service.

This is genuine similarity-based retrieval, not the exact-ID lookups
KnowledgeBaseRepository/reference_data.py already do - it exists to let a
semantic evaluator pull in KB context it doesn't already know the exact ID
of (e.g. "what official criteria/standards ground this dimension"), reusable
by any future semantic rule, not just the three this milestone implements.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

import chromadb

_COLLECTION_NAME = "knowledge_base"


@dataclass(frozen=True)
class EmbeddableRecord:
    """One unit of retrieval-relevant KB text, ready to embed. Built from a
    NormalizedRecord (app.services.knowledge_base.embedding_text) - kept as
    its own dataclass here rather than reusing NormalizedRecord directly, so
    this module's public contract doesn't couple to the KB ingestion
    pipeline's internal representation."""

    official_id: str
    text: str
    entity_type: str
    dimension: str | None
    provenance_category: str
    kb_version: str


@dataclass(frozen=True)
class RetrievedRecord:
    official_id: str
    text: str
    entity_type: str
    provenance_category: str
    kb_version: str


class VectorStore(Protocol):
    def upsert(self, records: Sequence[EmbeddableRecord]) -> None:
        """Replaces any existing embedding for each record's official_id."""
        ...

    def query(
        self,
        text: str,
        *,
        entity_type: str | None = None,
        dimension: str | None = None,
        n_results: int = 5,
    ) -> list[RetrievedRecord]:
        """Similarity search, optionally filtered by entity_type/dimension
        (RAG_AND_AI_DESIGN.md's "Filter by entity type and dimension").
        Returns fewer than n_results (possibly zero) if the collection has
        fewer matches or is empty - never an error, since "nothing relevant
        was found" is a normal, expected retrieval outcome (the caller's
        precondition/confidence logic decides what that means for the
        evaluation, not this layer)."""
        ...


def _build_where(entity_type: str | None, dimension: str | None) -> dict[str, object] | None:
    clauses: list[dict[str, object]] = []
    if entity_type is not None:
        clauses.append({"entity_type": entity_type})
    if dimension is not None:
        clauses.append({"dimension": dimension})
    if not clauses:
        return None
    if len(clauses) == 1:
        return clauses[0]
    return {"$and": clauses}


class ChromaVectorStore:
    """Talks to the docker-compose-provisioned ChromaDB service over HTTP.
    Uses Chroma's bundled default local embedding function (an ONNX model,
    not a hosted API) - embedding never sends analysis or KB content to a
    third party, only the ChromaDB service already running for this
    deployment."""

    def __init__(self, *, host: str, port: int) -> None:
        self._client = chromadb.HttpClient(host=host, port=port)
        self._collection = self._client.get_or_create_collection(_COLLECTION_NAME)

    def upsert(self, records: Sequence[EmbeddableRecord]) -> None:
        if not records:
            return
        self._collection.upsert(
            ids=[r.official_id for r in records],
            documents=[r.text for r in records],
            metadatas=[
                {
                    "entity_type": r.entity_type,
                    "dimension": r.dimension or "",
                    "provenance_category": r.provenance_category,
                    "kb_version": r.kb_version,
                }
                for r in records
            ],
        )

    def query(
        self,
        text: str,
        *,
        entity_type: str | None = None,
        dimension: str | None = None,
        n_results: int = 5,
    ) -> list[RetrievedRecord]:
        where = _build_where(entity_type, dimension)
        results = self._collection.query(
            query_texts=[text],
            n_results=n_results,
            where=where,  # type: ignore[arg-type]
        )
        ids = results["ids"][0]
        documents = results["documents"][0] if results["documents"] else []
        metadatas = results["metadatas"][0] if results["metadatas"] else []

        return [
            RetrievedRecord(
                official_id=id_,
                text=doc or "",
                entity_type=str(meta.get("entity_type", "")),
                provenance_category=str(meta.get("provenance_category", "")),
                kb_version=str(meta.get("kb_version", "")),
            )
            for id_, doc, meta in zip(ids, documents, metadatas, strict=True)
        ]
