from types import SimpleNamespace
from uuid import uuid4

from app.core.domain import (
    AcademicStatus,
    ReferenceResolutionStatus,
    ReferenceTargetType,
    SemanticConfidenceLevel,
)
from app.services.rules.identifiers import RuleIdentifier
from app.services.rules.reference_dependencies import gate_complete_information, gate_relationship
from app.services.rules.semantic_evaluators import SemanticRuleEvaluation
from app.services.rules.semantic_types import SemanticItemJudgment


def _evaluation(source_ids, *, status=AcademicStatus.SATISFIED):
    return SemanticRuleEvaluation(
        identifier=RuleIdentifier("REQ001", "RULE001", "Question-to-CLO Mapping"),
        status=status,
        confidence_level=SemanticConfidenceLevel.HIGH,
        confidence=1.0,
        evidence_ids=list(source_ids),
        explanation="All mappings validated.",
        recommendation_id=None,
        evaluator_type="semantic_ai",
        provider="test",
        model="test",
        prompt_template_version="test",
        kb_version="1.0.0",
        items=tuple(
            SemanticItemJudgment(
                source_evidence_id=source_id,
                target_evidence_ids=[uuid4()],
                status=AcademicStatus.SATISFIED,
                reasoning="Supported.",
            )
            for source_id in source_ids
        ),
        confidence_basis=("Complete source coverage.",),
    )


def _evidence(source_ids, question_ids):
    return [
        SimpleNamespace(id=source_id, question_id=question_id, evidence_type="question_text")
        for source_id, question_id in zip(source_ids, question_ids, strict=True)
    ]


def _snapshot(question_id, resolution_status):
    return SimpleNamespace(
        document_references=[
            SimpleNamespace(
                included=True,
                question_source_record_id=question_id,
                target_type=ReferenceTargetType.FIGURE,
                resolution_status=resolution_status,
            )
        ]
    )


def test_one_ambiguous_question_does_not_invalidate_other_relationships() -> None:
    source_ids = [uuid4(), uuid4()]
    question_ids = [uuid4(), uuid4()]
    result = gate_relationship(
        _evaluation(source_ids),
        _evidence(source_ids, question_ids),
        _snapshot(question_ids[1], ReferenceResolutionStatus.AMBIGUOUS),
    )

    assert result.status is AcademicStatus.PARTIALLY_SATISFIED
    assert result.items[0].status is AcademicStatus.SATISFIED
    assert result.items[1].status is AcademicStatus.NOT_VERIFIED


def test_relationship_is_not_verified_only_when_no_question_remains_judgeable() -> None:
    source_ids = [uuid4()]
    question_ids = [uuid4()]
    result = gate_relationship(
        _evaluation(source_ids),
        _evidence(source_ids, question_ids),
        _snapshot(question_ids[0], ReferenceResolutionStatus.UNRESOLVED),
    )

    assert result.status is AcademicStatus.NOT_VERIFIED


def test_ambiguous_material_makes_complete_information_partial_not_unverified() -> None:
    source_ids = [uuid4()]
    question_ids = [uuid4()]
    result = gate_complete_information(
        _evaluation(source_ids),
        _evidence(source_ids, question_ids),
        _snapshot(question_ids[0], ReferenceResolutionStatus.AMBIGUOUS),
    )

    assert result.status is AcademicStatus.PARTIALLY_SATISFIED
    assert result.items[0].status is AcademicStatus.PARTIALLY_SATISFIED


def test_missing_material_is_still_a_verified_failure() -> None:
    source_ids = [uuid4()]
    question_ids = [uuid4()]
    result = gate_complete_information(
        _evaluation(source_ids),
        _evidence(source_ids, question_ids),
        _snapshot(question_ids[0], ReferenceResolutionStatus.UNRESOLVED),
    )

    assert result.status is AcademicStatus.NOT_SATISFIED
    assert result.items[0].status is AcademicStatus.NOT_SATISFIED


def test_contextual_reference_does_not_gate_semantic_mapping() -> None:
    source_ids = [uuid4()]
    question_ids = [uuid4()]
    snapshot = SimpleNamespace(
        document_references=[
            SimpleNamespace(
                included=True,
                question_source_record_id=question_ids[0],
                target_type=ReferenceTargetType.FIGURE,
                normalized_target_label="figure:unlabeled",
                resolution_status=ReferenceResolutionStatus.AMBIGUOUS,
            )
        ]
    )

    result = gate_relationship(
        _evaluation(source_ids),
        _evidence(source_ids, question_ids),
        snapshot,
    )

    assert result.status is AcademicStatus.SATISFIED
    assert result.items[0].status is AcademicStatus.SATISFIED
