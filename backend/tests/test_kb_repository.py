from __future__ import annotations

from pathlib import Path

import pytest

from app.services.knowledge_base.entity_types import EntityType
from app.services.knowledge_base.models import ProvenanceCategory
from app.services.knowledge_base.normalizer import normalize_all
from app.services.knowledge_base.repository import (
    InvalidFilterValueError,
    KnowledgeBaseRepository,
    RecordFilter,
)
from app.services.knowledge_base.validator import load_and_validate

REAL_KB_SOURCE = Path(__file__).resolve().parents[2] / "knowledge_base" / "source"


@pytest.fixture(scope="module")
def repository() -> KnowledgeBaseRepository:
    records = normalize_all(load_and_validate(REAL_KB_SOURCE))
    return KnowledgeBaseRepository(records)


def test_filter_by_entity_type(repository: KnowledgeBaseRepository) -> None:
    results = repository.filter(RecordFilter(entity_type="Rule"))
    assert len(results) == 30
    assert all(r.entity_type == EntityType.RULE for r in results)


def test_filter_by_official_id(repository: KnowledgeBaseRepository) -> None:
    results = repository.filter(RecordFilter(official_id="RULE018"))
    assert len(results) == 1
    assert results[0].data["Rule_Name"] == "Correct Total Marks"


def test_filter_by_dimension(repository: KnowledgeBaseRepository) -> None:
    results = repository.filter(RecordFilter(dimension="Marks and Totals"))
    ids = {r.official_id for r in results}
    assert ids == {"REQ017", "REQ018"}


def test_filter_by_provenance_category(repository: KnowledgeBaseRepository) -> None:
    results = repository.filter(RecordFilter(provenance_category="system rule"))
    assert len(results) == 30
    assert all(r.provenance_category == ProvenanceCategory.SYSTEM_RULE for r in results)


def test_combined_filters_are_intersected(repository: KnowledgeBaseRepository) -> None:
    results = repository.filter(
        RecordFilter(entity_type="Requirement", dimension="Numbering and Structure")
    )
    assert [r.official_id for r in results] == ["REQ019"]


def test_valid_filter_with_no_matches_returns_empty_list(
    repository: KnowledgeBaseRepository,
) -> None:
    results = repository.filter(RecordFilter(dimension="Nonexistent Dimension"))
    assert results == []


def test_unfiltered_result_has_stable_deterministic_ordering(
    repository: KnowledgeBaseRepository,
) -> None:
    first = repository.filter(RecordFilter())
    second = repository.filter(RecordFilter())
    assert [r.official_id for r in first] == [r.official_id for r in second]
    # Sorted by (entity_type, official_id).
    keys = [(r.entity_type.value, r.official_id) for r in first]
    assert keys == sorted(keys)


def test_invalid_entity_type_raises_clear_error(repository: KnowledgeBaseRepository) -> None:
    with pytest.raises(InvalidFilterValueError, match="NotARealType"):
        repository.filter(RecordFilter(entity_type="NotARealType"))


def test_invalid_provenance_category_raises_clear_error(
    repository: KnowledgeBaseRepository,
) -> None:
    with pytest.raises(InvalidFilterValueError, match="not a real category"):
        repository.filter(RecordFilter(provenance_category="not a real category"))


def test_get_by_official_id_returns_none_when_missing(repository: KnowledgeBaseRepository) -> None:
    assert repository.get_by_official_id("REQ999") is None
    assert repository.get_by_official_id("REQ018") is not None
