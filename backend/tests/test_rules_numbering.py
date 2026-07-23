"""Direct, DB-free unit tests for evaluate_numbering - same in-memory
approach as test_rules_marks_total.py."""

from __future__ import annotations

import uuid

from app.core.domain import AcademicStatus, UploadedFileType
from app.models.evidence import Evidence
from app.models.question import Question
from app.services.rules.numbering import evaluate_numbering

ANALYSIS_ID = uuid.uuid4()


def _question(
    *, number_label: str, parent_id: uuid.UUID | None = None, confidence: float = 1.0
) -> Question:
    return Question(
        id=uuid.uuid4(),
        analysis_id=ANALYSIS_ID,
        parent_question_id=parent_id,
        number_label=number_label,
        question_text=f"{number_label} text",
        page_number=1,
        marks=None,
        sequence=1,
        confidence=confidence,
    )


def _text_evidence(question: Question) -> Evidence:
    return Evidence(
        id=uuid.uuid4(),
        analysis_id=ANALYSIS_ID,
        source_document=UploadedFileType.EXAM,
        evidence_type="question_text",
        page_number=1,
        item_reference=question.number_label,
        extracted_text=question.question_text,
        confidence=1.0,
    )


def test_zero_questions_is_not_verified() -> None:
    result = evaluate_numbering([], [])
    assert result.status == AcademicStatus.NOT_VERIFIED
    assert result.evidence_ids == []


def test_unique_numbering_is_satisfied() -> None:
    q1 = _question(number_label="Q1")
    q2 = _question(number_label="Q2")
    evidence = [_text_evidence(q1), _text_evidence(q2)]
    result = evaluate_numbering([q1, q2], evidence)
    assert result.status == AcademicStatus.SATISFIED
    assert set(result.evidence_ids) == {e.id for e in evidence}


def test_duplicate_top_level_label_is_not_satisfied() -> None:
    q1 = _question(number_label="Q1")
    q2a = _question(number_label="Q2")
    q2b = _question(number_label="Q2")
    result = evaluate_numbering([q1, q2a, q2b], [])
    assert result.status == AcademicStatus.NOT_SATISFIED
    assert "Q2" in result.explanation


def test_repeated_child_letters_under_different_parents_is_satisfied() -> None:
    parent1 = uuid.uuid4()
    parent2 = uuid.uuid4()
    q1 = _question(number_label="Q1")
    q1a = _question(number_label="Q1(a)", parent_id=parent1)
    q2 = _question(number_label="Q2")
    q2a = _question(number_label="Q2(a)", parent_id=parent2)

    result = evaluate_numbering([q1, q1a, q2, q2a], [])

    assert result.status == AcademicStatus.SATISFIED


def test_duplicate_child_label_under_same_parent_is_not_satisfied() -> None:
    parent_id = uuid.uuid4()
    q1 = _question(number_label="Q1")
    q1a_first = _question(number_label="Q1(a)", parent_id=parent_id)
    q1a_second = _question(number_label="Q1(a)", parent_id=parent_id)

    result = evaluate_numbering([q1, q1a_first, q1a_second], [])

    assert result.status == AcademicStatus.NOT_SATISFIED
    assert "Q1(a)" in result.explanation
