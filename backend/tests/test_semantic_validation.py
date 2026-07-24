from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, replace
from pathlib import Path

import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.domain import AcademicStatus, ExamType, UploadedFileType
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
    validate_semantic_output,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
KB_SOURCE = REPO_ROOT / "knowledge_base" / "source"


@dataclass(frozen=True)
class ValidationRows:
    analysis: Analysis
    other_analysis: Analysis
    question_evidence: Evidence
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
) -> Evidence:
    text = f"{label}: Explain cohesion. [CLO1]"
    question = Question(
        analysis_id=analysis.id,
        number_label=label,
        question_text=text,
        page_number=1,
        sequence=1,
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
        question_evidence = _question_with_evidence(session, analysis, label="Q1")
        other_evidence = _question_with_evidence(session, other, label="Q2")
        clo = Clo(
            analysis_id=analysis.id,
            code="CLO1",
            text="Explain software design principles.",
            page_number=2,
            confidence=0.9,
        )
        session.add(clo)
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
        for row in (
            analysis,
            other,
            question_evidence,
            clo_evidence,
            other_evidence,
        ):
            session.refresh(row)
            session.expunge(row)
    return ValidationRows(
        analysis=analysis,
        other_analysis=other,
        question_evidence=question_evidence,
        clo_evidence=clo_evidence,
        other_evidence=other_evidence,
    )


def _context(rows: ValidationRows) -> SemanticValidationContext:
    return SemanticValidationContext(
        analysis_id=rows.analysis.id,
        rule_spec=load_semantic_rule_spec(KB_SOURCE, CLO_RELEVANCE),
        prompt_template_version="semantic-rule002-v1",
        kb_version="1.0.0",
        allowed_evidence_ids=frozenset({rows.question_evidence.id, rows.clo_evidence.id}),
        allowed_evidence_types=frozenset({"question_text", "clo"}),
    )


def _payload(rows: ValidationRows, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "rule_id": "RULE002",
        "requirement_id": "REQ002",
        "status": "Satisfied",
        "confidence": 0.84,
        "evidence_ids": [
            str(rows.question_evidence.id),
            str(rows.clo_evidence.id),
        ],
        "explanation": "The question meaningfully elicits evidence for CLO1.",
        "recommendation_id": None,
        "provider": "fake",
        "model": "fake-semantic-v1",
        "prompt_template_version": "semantic-rule002-v1",
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
) -> object:
    return validate_semantic_output(
        json.dumps(payload),
        session=session,
        context=context or _context(rows),
        provider=FakeAiProvider(),
        kb_source_dir=KB_SOURCE,
    )


def test_valid_provider_output_is_released_as_a_typed_result(
    db_engine: Engine, validation_rows: ValidationRows
) -> None:
    with Session(db_engine) as session:
        result = _validate(session, validation_rows, _payload(validation_rows))
    assert result.status is AcademicStatus.SATISFIED
    assert result.evidence_ids == [
        validation_rows.question_evidence.id,
        validation_rows.clo_evidence.id,
    ]
    assert result.provider == "fake"


@pytest.mark.parametrize(
    "raw",
    [
        "{not-json",
        "[]",
        json.dumps({"rule_id": "RULE002"}),
    ],
)
def test_malformed_or_wrong_cardinality_output_is_rejected(
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
        ({"confidence": "0.84"}, "schema"),
        ({"confidence": True}, "schema"),
        ({"confidence": 1.1}, "schema"),
        ({"confidence": -0.1}, "schema"),
        ({"evidence_ids": []}, "at least one evidence"),
        ({"provider": "anthropic"}, "Provider/model provenance"),
        ({"model": "other"}, "Provider/model provenance"),
        ({"prompt_template_version": "wrong"}, "Prompt-template"),
        ({"kb_version": "wrong"}, "Knowledge-base"),
        ({"unexpected": "field"}, "schema"),
    ],
)
def test_invalid_claims_are_rejected_deterministically(
    db_engine: Engine,
    validation_rows: ValidationRows,
    overrides: dict[str, object],
    message: str,
) -> None:
    with Session(db_engine) as session:
        with pytest.raises(SemanticOutputValidationError, match=message):
            _validate(session, validation_rows, _payload(validation_rows, **overrides))


def test_duplicate_evidence_ids_are_rejected(
    db_engine: Engine, validation_rows: ValidationRows
) -> None:
    duplicate = [str(validation_rows.question_evidence.id)] * 2
    with Session(db_engine) as session:
        with pytest.raises(SemanticOutputValidationError, match="schema"):
            _validate(
                session,
                validation_rows,
                _payload(validation_rows, evidence_ids=duplicate),
            )


def test_unknown_evidence_id_is_rejected(
    db_engine: Engine, validation_rows: ValidationRows
) -> None:
    unknown = uuid.uuid4()
    context = replace(
        _context(validation_rows),
        allowed_evidence_ids=frozenset({unknown}),
    )
    with Session(db_engine) as session:
        with pytest.raises(SemanticOutputValidationError, match="unknown evidence"):
            _validate(
                session,
                validation_rows,
                _payload(validation_rows, evidence_ids=[str(unknown)]),
                context=context,
            )


def test_cross_analysis_evidence_ownership_is_rejected(
    db_engine: Engine, validation_rows: ValidationRows
) -> None:
    context = replace(
        _context(validation_rows),
        allowed_evidence_ids=frozenset({validation_rows.other_evidence.id}),
    )
    with Session(db_engine) as session:
        with pytest.raises(SemanticOutputValidationError, match="another analysis"):
            _validate(
                session,
                validation_rows,
                _payload(
                    validation_rows,
                    evidence_ids=[str(validation_rows.other_evidence.id)],
                ),
                context=context,
            )


def test_evidence_incompatible_with_the_evaluator_is_rejected(
    db_engine: Engine, validation_rows: ValidationRows
) -> None:
    context = replace(
        _context(validation_rows),
        allowed_evidence_types=frozenset({"clo"}),
    )
    with Session(db_engine) as session:
        with pytest.raises(SemanticOutputValidationError, match="incompatible"):
            _validate(
                session,
                validation_rows,
                _payload(
                    validation_rows,
                    evidence_ids=[str(validation_rows.question_evidence.id)],
                ),
                context=context,
            )


def test_invalid_or_inapplicable_recommendation_is_rejected(
    db_engine: Engine, validation_rows: ValidationRows
) -> None:
    with Session(db_engine) as session:
        with pytest.raises(SemanticOutputValidationError, match="does not apply"):
            _validate(
                session,
                validation_rows,
                _payload(validation_rows, recommendation_id="REC002"),
            )
        with pytest.raises(SemanticOutputValidationError, match="controlled recommendation"):
            _validate(
                session,
                validation_rows,
                _payload(
                    validation_rows,
                    status="Partially Satisfied",
                    recommendation_id="REC999",
                ),
            )


def test_controlled_recommendation_reference_is_accepted_for_applicable_status(
    db_engine: Engine, validation_rows: ValidationRows
) -> None:
    with Session(db_engine) as session:
        result = _validate(
            session,
            validation_rows,
            _payload(
                validation_rows,
                status="Partially Satisfied",
                recommendation_id="REC002",
            ),
        )
    assert result.recommendation_id == "REC002"


def test_clo_source_and_extracted_entity_provenance_are_required(
    db_engine: Engine, validation_rows: ValidationRows
) -> None:
    with Session(db_engine) as session:
        bad = Evidence(
            analysis_id=validation_rows.analysis.id,
            source_document=UploadedFileType.EXAM,
            evidence_type="clo",
            page_number=2,
            item_reference="CLO1",
            extracted_text="Explain software design principles.",
            confidence=0.9,
        )
        session.add(bad)
        session.commit()
        context = replace(
            _context(validation_rows),
            allowed_evidence_ids=frozenset({bad.id}),
        )
        with pytest.raises(SemanticOutputValidationError, match="TP-153"):
            _validate(
                session,
                validation_rows,
                _payload(validation_rows, evidence_ids=[str(bad.id)]),
                context=context,
            )
