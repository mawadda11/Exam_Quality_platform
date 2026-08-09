from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError

from app.core.domain import AcademicStatus, SemanticConfidenceLevel, UploadedFileType
from app.schemas.extraction_review import (
    ExtractionReviewEvidence,
    ExtractionReviewQuestion,
    ExtractionReviewSnapshot,
)
from app.schemas.finding import FindingEvaluationDetails


def _question(
    *,
    source_record_id: uuid.UUID | None = None,
    included: bool = True,
    parent_source_record_id: uuid.UUID | None = None,
) -> ExtractionReviewQuestion:
    return ExtractionReviewQuestion(
        source_record_id=source_record_id or uuid.uuid4(),
        included=included,
        parent_source_record_id=parent_source_record_id,
        number_label="Q1",
        question_text="Explain the purpose of a database index.",
        page_number=1,
        marks=5.0,
        sequence=0,
        extraction_confidence=0.95,
        geometry=None,
    )


def _evidence(
    *,
    question_source_record_id: uuid.UUID | None = None,
    included: bool = True,
) -> ExtractionReviewEvidence:
    return ExtractionReviewEvidence(
        source_record_id=uuid.uuid4(),
        included=included,
        question_source_record_id=question_source_record_id,
        source_document=UploadedFileType.EXAM,
        evidence_type="question_text",
        page_number=1,
        item_reference="Q1",
        extracted_text="Explain the purpose of a database index.",
        extraction_confidence=0.95,
        geometry=None,
    )


def _snapshot(
    *,
    questions: list[ExtractionReviewQuestion] | None = None,
    evidence: list[ExtractionReviewEvidence] | None = None,
) -> ExtractionReviewSnapshot:
    return ExtractionReviewSnapshot(
        schema_version=1,
        questions=questions or [],
        evidence=evidence or [],
        clos=[],
        topics=[],
        assessment_records=[],
    )


def test_semantic_confidence_level_is_the_exact_authoritative_vocabulary() -> None:
    assert [level.value for level in SemanticConfidenceLevel] == ["High", "Medium", "Low"]


def test_snapshot_accepts_empty_collections_without_fabricating_placeholders() -> None:
    snapshot = _snapshot()

    assert snapshot.questions == []
    assert snapshot.clos == []
    assert snapshot.topics == []
    assert snapshot.assessment_records == []
    assert snapshot.model_dump(mode="json")["schema_version"] == 1


def test_snapshot_round_trips_real_source_records_as_json() -> None:
    question = _question()
    evidence = _evidence(question_source_record_id=question.source_record_id)
    snapshot = _snapshot(questions=[question], evidence=[evidence])

    restored = ExtractionReviewSnapshot.model_validate_json(snapshot.model_dump_json())

    assert restored == snapshot
    assert restored.evidence[0].question_source_record_id == question.source_record_id


def test_snapshot_rejects_duplicate_source_record_ids() -> None:
    source_record_id = uuid.uuid4()

    with pytest.raises(ValidationError, match="source_record_id values must be unique"):
        _snapshot(
            questions=[
                _question(source_record_id=source_record_id),
                _question(source_record_id=source_record_id),
            ]
        )


def test_snapshot_rejects_dangling_question_and_evidence_references() -> None:
    with pytest.raises(ValidationError, match="parent references must resolve"):
        _snapshot(questions=[_question(parent_source_record_id=uuid.uuid4())])

    with pytest.raises(ValidationError, match="Evidence question references must resolve"):
        _snapshot(evidence=[_evidence(question_source_record_id=uuid.uuid4())])


def test_snapshot_rejects_included_records_that_depend_on_excluded_questions() -> None:
    parent = _question(included=False)
    child = _question(parent_source_record_id=parent.source_record_id)

    with pytest.raises(ValidationError, match="excluded parent"):
        _snapshot(questions=[parent, child])

    with pytest.raises(ValidationError, match="excluded question"):
        _snapshot(
            questions=[parent],
            evidence=[_evidence(question_source_record_id=parent.source_record_id)],
        )


def test_snapshot_rejects_question_hierarchy_cycles_even_when_links_resolve() -> None:
    first = _question()
    second = _question(parent_source_record_id=first.source_record_id)
    first = first.model_copy(update={"parent_source_record_id": second.source_record_id})

    with pytest.raises(ValidationError, match="must not contain a cycle"):
        _snapshot(questions=[first, second])


def test_snapshot_rejects_invalid_values_and_unknown_fields() -> None:
    payload = _snapshot().model_dump(mode="json")
    payload["unknown"] = "not allowed"
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        ExtractionReviewSnapshot.model_validate(payload)

    question_payload = _question().model_dump(mode="json")
    question_payload["page_number"] = 0
    question_payload["extraction_confidence"] = 1.1
    with pytest.raises(ValidationError):
        ExtractionReviewQuestion.model_validate(question_payload)


def test_evaluation_details_has_the_versioned_governed_core_contract() -> None:
    evidence_id = uuid.uuid4()
    details = FindingEvaluationDetails(
        schema_version=1,
        decision=AcademicStatus.SATISFIED,
        evidence_used=[evidence_id],
        reasoning="The cited source evidence directly satisfies the governed rule.",
        recommendation=None,
    )

    assert details.decision is AcademicStatus.SATISFIED
    assert details.evidence_used == [evidence_id]
    assert set(details.model_dump()) == {
        "schema_version",
        "decision",
        "evidence_used",
        "reasoning",
        "reasoning_ar",
        "recommendation",
        "confidence_basis",
        "item_judgments",
        "retrieved_knowledge_ids",
    }


def test_evaluation_details_rejects_duplicates_blank_text_and_extra_fields() -> None:
    evidence_id = uuid.uuid4()
    base = {
        "schema_version": 1,
        "decision": AcademicStatus.NOT_VERIFIED,
        "evidence_used": [evidence_id, evidence_id],
        "reasoning": " ",
        "recommendation": "",
        "confidence": SemanticConfidenceLevel.LOW,
    }

    with pytest.raises(ValidationError):
        FindingEvaluationDetails.model_validate(base)
