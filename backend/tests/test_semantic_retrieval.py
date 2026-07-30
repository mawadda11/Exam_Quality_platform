from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

from app.services.knowledge_base.embedding_text import (
    build_embeddable_records,
    embedding_text,
    stable_chroma_id,
)
from app.services.knowledge_base.entity_types import EntityType
from app.services.knowledge_base.runtime import load_kb_snapshot
from app.services.knowledge_base.vector_store import (
    ChromaVectorStore,
    EmbeddableRecord,
    InMemoryVectorStore,
    _local_embedding,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
KB_SOURCE = REPO_ROOT / "knowledge_base" / "source"


def _record(
    *,
    record_id: str,
    version: str,
    text: str,
    entity_type: str = "Rule",
    dimension: str | None = "CLO Alignment",
    requirement_id: str | None = "REQ002",
    rule_id: str | None = "RULE002",
) -> EmbeddableRecord:
    return EmbeddableRecord(
        record_id=record_id,
        official_id=rule_id or requirement_id or record_id,
        text=text,
        entity_type=entity_type,
        dimension=dimension,
        requirement_id=requirement_id,
        rule_id=rule_id,
        provenance_category="Derived",
        kb_version=version,
        kb_hash=f"hash-{version}",
        source_workbook="07_evaluation_rules.xlsx",
        source_row_number=3,
        record_hash=f"record-{record_id}",
    )


def test_embedding_text_uses_reviewed_fields_and_preserves_source_identity() -> None:
    snapshot = load_kb_snapshot(KB_SOURCE)
    by_id = {
        (record.entity_type, record.official_id): record for record in snapshot.embeddable_records
    }

    rule = by_id[("Rule", "RULE002")]
    assert "Official ID: RULE002" in rule.text
    assert "Satisfied Condition:" in rule.text
    assert rule.requirement_id == "REQ002"
    assert rule.dimension == "CLO Alignment"
    assert rule.source_workbook == "07_evaluation_rules.xlsx"
    assert rule.kb_version == snapshot.version
    assert rule.kb_hash == snapshot.aggregate_hash

    # Recommendations are controlled exact-ID data and are intentionally not
    # embedded; model-selected free-form recommendation text is never allowed.
    assert not any(record.entity_type == "Recommendation" for record in by_id.values())


def test_embedding_projection_excludes_unreviewed_entity_types() -> None:
    snapshot = load_kb_snapshot(KB_SOURCE)
    recommendation = next(
        record for record in snapshot.records if record.entity_type is EntityType.RECOMMENDATION
    )
    assert embedding_text(recommendation) is None
    assert all(
        record.official_id != recommendation.official_id for record in snapshot.embeddable_records
    )


def test_stable_chroma_ids_are_deterministic_and_version_isolated() -> None:
    first = stable_chroma_id("1.0.0", EntityType.RULE, "RULE002")
    assert first == stable_chroma_id("1.0.0", EntityType.RULE, "RULE002")
    assert first != stable_chroma_id("1.0.1", EntityType.RULE, "RULE002")
    assert first != stable_chroma_id("1.0.0", EntityType.RULE, "RULE004")


def test_all_embeddable_records_have_deterministic_unique_ids() -> None:
    snapshot = load_kb_snapshot(KB_SOURCE)
    rebuilt = build_embeddable_records(
        snapshot.records,
        kb_version=snapshot.version,
        kb_hash=snapshot.aggregate_hash,
    )
    assert [record.record_id for record in rebuilt] == [
        record.record_id for record in snapshot.embeddable_records
    ]
    assert len({record.record_id for record in rebuilt}) == len(rebuilt)


def test_in_memory_retrieval_filters_by_version_and_governance_metadata() -> None:
    store = InMemoryVectorStore()
    records = [
        _record(record_id="v1-rule2", version="1", text="CLO relevance evidence"),
        _record(
            record_id="v1-rule4",
            version="1",
            text="question format CLO evidence",
            dimension="Assessment Alignment",
            requirement_id="REQ004",
            rule_id="RULE004",
        ),
        _record(record_id="v2-rule2", version="2", text="CLO relevance evidence"),
    ]
    store.replace_version(records, kb_version="1")

    result = store.query(
        "CLO relevance",
        kb_version="1",
        entity_type="Rule",
        dimension="CLO Alignment",
        requirement_id="REQ002",
        rule_id="RULE002",
    )
    assert [item.record_id for item in result] == ["v1-rule2"]
    assert result[0].kb_version == "1"
    assert result[0].official_id == "RULE002"
    assert store.query("CLO relevance", kb_version="missing") == []


def test_replacing_one_version_removes_its_stale_records_only() -> None:
    store = InMemoryVectorStore()
    version_one = _record(record_id="v1-old", version="1", text="old relevance")
    version_two = _record(record_id="v2", version="2", text="other relevance")
    store.replace_version([version_one, version_two], kb_version="1")
    replacement = _record(record_id="v1-new", version="1", text="new relevance")

    store.replace_version([replacement], kb_version="1")

    assert [item.record_id for item in store.query("relevance", kb_version="1")] == ["v1-new"]
    assert [item.record_id for item in store.query("relevance", kb_version="2")] == ["v2"]


def test_empty_retrieval_and_invalid_result_limit_are_explicit() -> None:
    store = InMemoryVectorStore()
    store.replace_version(
        [_record(record_id="one", version="1", text="CLO relevance")],
        kb_version="1",
    )
    assert store.query("unrelated-token", kb_version="1") == []
    with pytest.raises(ValueError, match="at least 1"):
        store.query("CLO", kb_version="1", n_results=0)


class _FakeCollection:
    def __init__(self) -> None:
        self.delete_calls: list[Mapping[str, object]] = []
        self.upserts: list[dict[str, Any]] = []
        self.query_kwargs: dict[str, Any] = {}

    def delete(self, *, where: Mapping[str, object]) -> None:
        self.delete_calls.append(where)

    def upsert(self, **kwargs: Any) -> None:
        self.upserts.append(kwargs)

    def count(self) -> int:
        return 1

    def query(self, **kwargs: Any) -> dict[str, object]:
        self.query_kwargs = kwargs
        metadata = {
            "official_id": "RULE002",
            "entity_type": "Rule",
            "dimension": "CLO Alignment",
            "requirement_id": "REQ002",
            "rule_id": "RULE002",
            "provenance_category": "Derived",
            "kb_version": "1",
            "kb_hash": "hash-1",
            "source_workbook": "07_evaluation_rules.xlsx",
            "source_row_number": 3,
            "record_hash": "record-one",
        }
        return {
            "ids": [["one"]],
            "documents": [["CLO relevance"]],
            "metadatas": [[metadata]],
        }


class _FakeChromaClient:
    def __init__(self, collection: _FakeCollection) -> None:
        self.collection = collection

    def get_or_create_collection(self, name: str) -> _FakeCollection:
        assert name == "knowledge_base"
        return self.collection


def test_chroma_rebuild_deletes_same_version_then_upserts_with_filtered_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    collection = _FakeCollection()
    client = _FakeChromaClient(collection)
    monkeypatch.setattr(
        "app.services.knowledge_base.vector_store._build_chroma_http_client",
        lambda *, host, port: client,
    )
    store = ChromaVectorStore(host="chromadb", port=8000)
    record = _record(record_id="one", version="1", text="CLO relevance")

    store.replace_version([record], kb_version="1")
    result = store.query(
        "CLO relevance",
        kb_version="1",
        entity_type="Rule",
        dimension="CLO Alignment",
        requirement_id="REQ002",
        rule_id="RULE002",
    )

    assert collection.delete_calls == [{"kb_version": "1"}]
    assert collection.upserts[0]["ids"] == ["one"]
    assert collection.upserts[0]["metadatas"][0]["record_hash"] == "record-one"
    assert collection.upserts[0]["embeddings"] == [_local_embedding("CLO relevance")]
    assert "query_texts" not in collection.query_kwargs
    assert collection.query_kwargs["query_embeddings"] == [_local_embedding("CLO relevance")]
    assert collection.query_kwargs["where"] == {
        "$and": [
            {"kb_version": "1"},
            {"entity_type": "Rule"},
            {"dimension": "CLO Alignment"},
            {"requirement_id": "REQ002"},
            {"rule_id": "RULE002"},
        ]
    }
    assert result[0].record_id == "one"
    assert result[0].source_row_number == 3


def test_local_embedding_is_deterministic_unicode_aware_and_normalized() -> None:
    first = _local_embedding("اختبار نصفي لقواعد البيانات")
    second = _local_embedding("اختبار نصفي لقواعد البيانات")
    diacritics = _local_embedding("اِخْتِبَار نِصْفِي لِقَوَاعِدِ الْبَيَانَات")

    assert first == second
    assert len(first) == 384
    assert sum(value * value for value in first) == pytest.approx(1.0)
    assert first == diacritics
    assert first != _local_embedding("استعلامات SQL متقدمة")
