from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, replace
from pathlib import Path

import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.domain import (
    AcademicStatus,
    ExamType,
    SemanticConfidenceLevel,
    UploadedFileType,
)
from app.models.analysis import Analysis
from app.models.clo import Clo
from app.models.course import Course
from app.models.evidence import Evidence
from app.models.question import Question
from app.models.user import User
from app.services.ai.fake_provider import FakeAiProvider
from app.services.rules.identifiers import CLO_RELEVANCE
from app.services.rules.semantic_governance import load_semantic_rule_spec
from app.services.rules.semantic_types import SemanticValidationContext
from app.services.rules.semantic_validation import (
    SemanticOutputValidationError,
    aggregate_item_statuses,
    validate_semantic_output,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
KB_SOURCE = REPO_ROOT / "knowledge_base" / "source"


@dataclass(frozen=True)
class ValidationRows:
    analysis: Analysis
    other_analysis: Analysis
    question_evidence: Evidence
    second_question_evidence: Evidence
    clo_evidence: Evidence
    other_evidence: Evidence


def _analysis(session: Session, suffix: str) -> Analysis:
    user = User(email=f"semantic-{suffix}@kau.edu.sa", display_name="Semantic Test")
    course = Course(code=f"SEM-{suffix}", name="Semantic Validation")
    session.add_all([user, course])
    session.flush()
    analysis = Analysis(
        user_id=user.id,
        course_id=course.id,
        exam_type=ExamType.MIDTERM,
        term="Test",
    )
    session.add(analysis)
    session.flush()
    return analysis


def _question_with_evidence(
    session: Session,
    analysis: Analysis,
    *,
    label: str,
    sequence: int,
) -> Evidence:
    text = f"{label}: Explain software cohesion and coupling."
    question = Question(
        analysis_id=analysis.id,
        number_label=label,
        question_text=text,
        page_number=1,
        sequence=sequence,
        confidence=0.95,
    )
    session.add(question)
    session.flush()
    evidence = Evidence(
        analysis_id=analysis.id,
        question_id=question.id,
        source_document=UploadedFileType.EXAM,
        evidence_type="question_text",
        page_number=1,
        item_reference=label,
        extracted_text=text,
        confidence=0.95,
    )
    session.add(evidence)
    session.flush()
    return evidence


@pytest.fixture()
def validation_rows(db_engine: Engine) -> ValidationRows:
    with Session(db_engine) as session:
        analysis = _analysis(session, "one")
        other = _analysis(session, "two")
        question_evidence = _question_with_evidence(session, analysis, label="Q1", sequence=1)
        second_question_evidence = _question_with_evidence(
            session, analysis, label="Q2", sequence=2
        )
        other_evidence = _question_with_evidence(session, other, label="Q3", sequence=1)
        clo = Clo(
            analysis_id=analysis.id,
            code="CLO1",
            text="Explain core software design principles including cohesion and coupling.",
            page_number=2,
            confidence=0.9,
        )
        session.add(clo)
        session.flush()
        clo_evidence = Evidence(
            analysis_id=analysis.id,
            source_document=UploadedFileType.TP153,
            evidence_type="clo",
            page_number=2,
            item_reference="CLO1",
            extracted_text=clo.text,
            confidence=0.9,
        )
        session.add(clo_evidence)
        session.commit()
        rows = (
            analysis,
            other,
            question_evidence,
            second_question_evidence,
            clo_evidence,
            other_evidence,
        )
        for row in rows:
            session.refresh(row)
            session.expunge(row)
    return ValidationRows(*rows)


def _context(
    rows: ValidationRows,
    *,
    both_questions: bool = False,
) -> SemanticValidationContext:
    sources = {rows.question_evidence.id}
    if both_questions:
        sources.add(rows.second_question_evidence.id)
    return SemanticValidationContext(
        analysis_id=rows.analysis.id,
        rule_spec=load_semantic_rule_spec(KB_SOURCE, CLO_RELEVANCE),
        prompt_template_version="semantic-rule002-v2",
        kb_version="1.0.0",
        allowed_evidence_ids=frozenset({*sources, rows.clo_evidence.id}),
        allowed_evidence_types=frozenset({"question_text", "clo"}),
        required_source_evidence_ids=frozenset(sources),
        allowed_target_evidence_ids=frozenset({rows.clo_evidence.id}),
        relationship_required=True,
    )


def _item(
    rows: ValidationRows,
    *,
    source_id: uuid.UUID | None = None,
    status: str = "Satisfied",
    targets: list[uuid.UUID] | None = None,
) -> dict[str, object]:
    return {
        "source_evidence_id": str(source_id or rows.question_evidence.id),
        "target_evidence_ids": [
            str(value) for value in (targets if targets is not None else [rows.clo_evidence.id])
        ],
        "status": status,
        "reasoning": "The confirmed question and CLO share substantive software-design concepts.",
    }


def _payload(
    rows: ValidationRows,
    *,
    items: list[dict[str, object]] | None = None,
    **overrides: object,
) -> dict[str, object]:
    selected_items = items or [_item(rows)]
    evidence_ids = sorted(
        {str(item["source_evidence_id"]) for item in selected_items}
        | {
            str(target)
            for item in selected_items
            for target in item["target_evidence_ids"]  # type: ignore[index]
        }
    )
    payload: dict[str, object] = {
        "rule_id": "RULE002",
        "requirement_id": "REQ002",
        "status": "Satisfied",
        "evidence_ids": evidence_ids,
        "explanation": "The expected responses provide evidence for the supplied CLO.",
        "recommendation_id": None,
        "items": selected_items,
        "provider": "fake",
        "model": "fake-semantic-v2",
        "prompt_template_version": "semantic-rule002-v2",
        "kb_version": "1.0.0",
    }
    payload.update(overrides)
    return payload


def _validate(
    session: Session,
    rows: ValidationRows,
    payload: object,
    *,
    context: SemanticValidationContext | None = None,
):
    return validate_semantic_output(
        json.dumps(payload),
        session=session,
        context=context or _context(rows),
        provider=FakeAiProvider(),
        kb_source_dir=KB_SOURCE,
    )


def test_complete_valid_output_derives_high_confidence(
    db_engine: Engine, validation_rows: ValidationRows
) -> None:
    with Session(db_engine) as session:
        result = _validate(session, validation_rows, _payload(validation_rows))

    assert result.status is AcademicStatus.SATISFIED
    assert result.confidence_level is SemanticConfidenceLevel.HIGH
    assert result.legacy_confidence == 1.0
    assert result.provider == "fake"
    assert len(result.items) == 1
    assert result.evidence_ids == sorted(
        [validation_rows.question_evidence.id, validation_rows.clo_evidence.id],
        key=str,
    )


def test_provider_aggregate_status_is_advisory(
    db_engine: Engine,
    validation_rows: ValidationRows,
) -> None:
    payload = _payload(
        validation_rows,
        status="Not Satisfied",
    )

    with Session(db_engine) as session:
        result = _validate(
            session,
            validation_rows,
            payload,
        )

    assert result.status is AcademicStatus.SATISFIED
    assert result.items[0].status is AcademicStatus.SATISFIED


def test_missing_required_source_forces_low_not_verified(
    db_engine: Engine, validation_rows: ValidationRows
) -> None:
    context = _context(validation_rows, both_questions=True)
    payload = _payload(validation_rows)
    with Session(db_engine) as session:
        result = _validate(session, validation_rows, payload, context=context)

    assert result.status is AcademicStatus.NOT_VERIFIED
    assert result.confidence_level is SemanticConfidenceLevel.LOW
    assert result.legacy_confidence == 0.0
    assert any("Missing source judgments" in value for value in result.confidence_basis)


def test_complete_mixed_output_with_not_verified_derives_medium_confidence(
    db_engine: Engine, validation_rows: ValidationRows
) -> None:
    items = [
        _item(validation_rows),
        _item(
            validation_rows,
            source_id=validation_rows.second_question_evidence.id,
            status="Not Verified",
            targets=[],
        ),
    ]
    payload = _payload(
        validation_rows,
        items=items,
        status="Partially Satisfied",
    )
    with Session(db_engine) as session:
        result = _validate(
            session,
            validation_rows,
            payload,
            context=_context(validation_rows, both_questions=True),
        )

    assert result.status is AcademicStatus.PARTIALLY_SATISFIED
    assert result.confidence_level is SemanticConfidenceLevel.MEDIUM
    assert result.legacy_confidence == 0.5


@pytest.mark.parametrize(
    "raw",
    ["{not-json", "[]", json.dumps({"rule_id": "RULE002"})],
)
def test_malformed_output_is_rejected(
    db_engine: Engine,
    validation_rows: ValidationRows,
    raw: str,
) -> None:
    with Session(db_engine) as session:
        with pytest.raises(SemanticOutputValidationError, match="schema"):
            validate_semantic_output(
                raw,
                session=session,
                context=_context(validation_rows),
                provider=FakeAiProvider(),
                kb_source_dir=KB_SOURCE,
            )


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"rule_id": "RULE008"}, "rule ID"),
        ({"requirement_id": "REQ008"}, "requirement ID"),
        ({"status": "Unknown"}, "schema"),
        ({"provider": "anthropic"}, "Provider/model provenance"),
        ({"model": "other"}, "Provider/model provenance"),
        ({"prompt_template_version": "wrong"}, "Prompt-template"),
        ({"kb_version": "wrong"}, "Knowledge-base"),
        ({"unexpected": "field"}, "schema"),
        ({"confidence": 0.9}, "schema"),
    ],
)
def test_invalid_contract_claims_are_rejected(
    db_engine: Engine,
    validation_rows: ValidationRows,
    overrides: dict[str, object],
    message: str,
) -> None:
    with Session(db_engine) as session:
        with pytest.raises(SemanticOutputValidationError, match=message):
            _validate(session, validation_rows, _payload(validation_rows, **overrides))


def test_provider_evidence_ids_are_advisory(
    db_engine: Engine, validation_rows: ValidationRows
) -> None:
    with Session(db_engine) as session:
        result = _validate(
            session,
            validation_rows,
            _payload(
                validation_rows,
                evidence_ids=[str(validation_rows.question_evidence.id)],
            ),
        )

    assert result.evidence_ids == sorted(
        [
            validation_rows.question_evidence.id,
            validation_rows.clo_evidence.id,
        ],
        key=str,
    )


def test_positive_relationship_without_target_is_not_verified(
    db_engine: Engine, validation_rows: ValidationRows
) -> None:
    item = _item(validation_rows, targets=[])

    with Session(db_engine) as session:
        result = _validate(
            session,
            validation_rows,
            _payload(validation_rows, items=[item]),
        )

    assert result.status is AcademicStatus.NOT_VERIFIED
    assert result.confidence_level is SemanticConfidenceLevel.LOW
    assert result.items[0].status is AcademicStatus.NOT_VERIFIED
    assert result.items[0].target_evidence_ids == []


def test_target_outside_controlled_set_is_rejected(
    db_engine: Engine, validation_rows: ValidationRows
) -> None:
    item = _item(validation_rows, targets=[validation_rows.other_evidence.id])
    context = replace(
        _context(validation_rows),
        allowed_evidence_ids=frozenset(
            {
                validation_rows.question_evidence.id,
                validation_rows.clo_evidence.id,
                validation_rows.other_evidence.id,
            }
        ),
    )
    with Session(db_engine) as session:
        with pytest.raises(SemanticOutputValidationError, match="target outside"):
            _validate(
                session,
                validation_rows,
                _payload(validation_rows, items=[item]),
                context=context,
            )


def test_cross_analysis_evidence_is_rejected(
    db_engine: Engine, validation_rows: ValidationRows
) -> None:
    item = _item(
        validation_rows,
        source_id=validation_rows.other_evidence.id,
        targets=[],
        status="Not Satisfied",
    )
    context = SemanticValidationContext(
        analysis_id=validation_rows.analysis.id,
        rule_spec=load_semantic_rule_spec(KB_SOURCE, CLO_RELEVANCE),
        prompt_template_version="semantic-rule002-v2",
        kb_version="1.0.0",
        allowed_evidence_ids=frozenset({validation_rows.other_evidence.id}),
        allowed_evidence_types=frozenset({"question_text"}),
        required_source_evidence_ids=frozenset({validation_rows.other_evidence.id}),
        allowed_target_evidence_ids=frozenset(),
        relationship_required=False,
    )
    with Session(db_engine) as session:
        with pytest.raises(SemanticOutputValidationError, match="another analysis"):
            _validate(
                session,
                validation_rows,
                _payload(validation_rows, items=[item], status="Not Satisfied"),
                context=context,
            )


def test_controlled_recommendation_is_accepted_only_for_final_status(
    db_engine: Engine, validation_rows: ValidationRows
) -> None:
    partial_item = _item(validation_rows, status="Partially Satisfied")
    with Session(db_engine) as session:
        result = _validate(
            session,
            validation_rows,
            _payload(
                validation_rows,
                items=[partial_item],
                status="Partially Satisfied",
                recommendation_id="REC002",
            ),
        )
        assert result.recommendation_id == "REC002"

        with pytest.raises(SemanticOutputValidationError, match="does not apply"):
            _validate(
                session,
                validation_rows,
                _payload(validation_rows, recommendation_id="REC002"),
            )


def test_confirmed_domain_provenance_is_required(
    db_engine: Engine, validation_rows: ValidationRows
) -> None:
    with Session(db_engine) as session:
        bad = Evidence(
            analysis_id=validation_rows.analysis.id,
            source_document=UploadedFileType.EXAM,
            evidence_type="clo",
            page_number=2,
            item_reference="CLO1",
            extracted_text=(
                "Explain core software design principles including cohesion and coupling."
            ),
            confidence=0.9,
        )
        session.add(bad)
        session.commit()
        item = _item(validation_rows, targets=[bad.id])
        context = replace(
            _context(validation_rows),
            allowed_evidence_ids=frozenset({validation_rows.question_evidence.id, bad.id}),
            allowed_target_evidence_ids=frozenset({bad.id}),
        )
        with pytest.raises(SemanticOutputValidationError, match="TP-153"):
            _validate(
                session,
                validation_rows,
                _payload(validation_rows, items=[item]),
                context=context,
            )


def test_status_aggregation_is_threshold_free() -> None:
    class Item:
        def __init__(self, status: AcademicStatus) -> None:
            self.status = status

    assert aggregate_item_statuses([Item(AcademicStatus.SATISFIED)]) is AcademicStatus.SATISFIED
    assert (
        aggregate_item_statuses(
            [Item(AcademicStatus.SATISFIED), Item(AcademicStatus.NOT_SATISFIED)]
        )
        is AcademicStatus.PARTIALLY_SATISFIED
    )
    assert (
        aggregate_item_statuses([Item(AcademicStatus.NOT_APPLICABLE)])
        is AcademicStatus.NOT_APPLICABLE
    )
