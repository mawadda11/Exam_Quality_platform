"""Internal, in-process, read-only query/filter surface over normalized KB
records. No HTTP endpoint, no database, no embeddings/similarity/ranking -
exact deterministic filtering only. Reusable as-is by M8; implements no
alignment logic of its own.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from app.services.knowledge_base.entity_types import EntityType
from app.services.knowledge_base.models import NormalizedRecord, ProvenanceCategory


class InvalidFilterValueError(ValueError):
    """Raised when a filter value isn't a known entity_type or
    provenance_category - never silently ignored or treated as no-match."""


@dataclass(frozen=True)
class RecordFilter:
    entity_type: str | None = None
    dimension: str | None = None
    official_id: str | None = None
    provenance_category: str | None = None


def _parse_entity_type(value: str | None) -> EntityType | None:
    if value is None:
        return None
    try:
        return EntityType(value)
    except ValueError as exc:
        valid = sorted(e.value for e in EntityType)
        raise InvalidFilterValueError(
            f"{value!r} is not a known entity_type. Valid values: {valid}."
        ) from exc


def _parse_provenance(value: str | None) -> ProvenanceCategory | None:
    if value is None:
        return None
    try:
        return ProvenanceCategory(value)
    except ValueError as exc:
        valid = sorted(p.value for p in ProvenanceCategory)
        raise InvalidFilterValueError(
            f"{value!r} is not a known provenance_category. Valid values: {valid}."
        ) from exc


class KnowledgeBaseRepository:
    """Holds one immutable, already-normalized snapshot of KB records."""

    def __init__(self, records: Sequence[NormalizedRecord]) -> None:
        # Stable deterministic ordering, independent of input order.
        self._records: tuple[NormalizedRecord, ...] = tuple(
            sorted(records, key=lambda r: (r.entity_type.value, r.official_id))
        )

    def __len__(self) -> int:
        return len(self._records)

    def filter(self, criteria: RecordFilter) -> list[NormalizedRecord]:
        entity_type = _parse_entity_type(criteria.entity_type)
        provenance_category = _parse_provenance(criteria.provenance_category)

        results: tuple[NormalizedRecord, ...] = self._records
        if entity_type is not None:
            results = tuple(r for r in results if r.entity_type == entity_type)
        if criteria.dimension is not None:
            results = tuple(r for r in results if r.data.get("Dimension") == criteria.dimension)
        if criteria.official_id is not None:
            results = tuple(r for r in results if r.official_id == criteria.official_id)
        if provenance_category is not None:
            results = tuple(r for r in results if r.provenance_category == provenance_category)
        return list(results)

    def get_by_official_id(self, official_id: str) -> NormalizedRecord | None:
        for record in self._records:
            if record.official_id == official_id:
                return record
        return None
