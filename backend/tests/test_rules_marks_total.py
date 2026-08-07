"""Direct, DB-free unit tests for evaluate_marks_and_total - constructs
Question/Evidence ORM instances in memory (never added to a session) since
the rule function is pure and never touches the database."""

from __future__ import annotations

import uuid

from app.core.domain import AcademicStatus, UploadedFileType
from app.models.evidence import Evidence
from app.models.question import Question
from app.services.rules.marks_total import evaluate_marks_and_total

ANALYSIS_ID = uuid.uuid4()


def _question(
    *,
    number_label: str,
    marks: float | None,
    confidence: float = 1.0,
    parent_id: uuid.UUID | None = None,
) -> Question:
    return Question(
        id=uuid.uuid4(),
        analysis_id=ANALYSIS_ID,
        parent_question_id=parent_id,
        number_label=number_label,
        question_text=f"{number_label} text",
        page_number=1,
        marks=marks,
        sequence=1,
        confidence=confidence,
    )


def _evidence(
    *, evidence_type: str, item_reference: str, text: str = "", confidence: float = 1.0
) -> Evidence:
    return Evidence(
        id=uuid.uuid4(),
        analysis_id=ANALYSIS_ID,
        source_document=UploadedFileType.EXAM,
        evidence_type=evidence_type,
        page_number=1,
        item_reference=item_reference,
        extracted_text=text,
        confidence=confidence,
    )


def _declared_total(value: str) -> Evidence:
    return _evidence(
        evidence_type="declared_total", item_reference="total", text=f"Total Marks: {value}"
    )


def test_no_declared_total_is_not_applicable() -> None:
    q1 = _question(number_label="Q1", marks=5.0)
    result = evaluate_marks_and_total([q1], [])
    assert result.status == AcademicStatus.NOT_APPLICABLE
    assert result.evidence_ids == []


def test_matching_total_is_satisfied() -> None:
    q1 = _question(number_label="Q1", marks=5.0)
    q2 = _question(number_label="Q2", marks=3.0)
    total = _declared_total("8")
    result = evaluate_marks_and_total([q1, q2], [total])
    assert result.status == AcademicStatus.SATISFIED
    assert total.id in result.evidence_ids


def test_mismatched_total_is_not_satisfied() -> None:
    q1 = _question(number_label="Q1", marks=5.0)
    q2 = _question(number_label="Q2", marks=3.0)
    total = _declared_total("20")
    result = evaluate_marks_and_total([q1, q2], [total])
    assert result.status == AcademicStatus.NOT_SATISFIED


def test_missing_leaf_marks_is_not_verified() -> None:
    q1 = _question(number_label="Q1", marks=5.0)
    q2 = _question(number_label="Q2", marks=None)
    total = _declared_total("10")
    result = evaluate_marks_and_total([q1, q2], [total])
    assert result.status == AcademicStatus.NOT_VERIFIED
    assert "Q2" in result.explanation


def test_single_ambiguous_mark_on_mismatch_is_partially_satisfied() -> None:
    q1 = _question(number_label="Q1", marks=5.0, confidence=1.0)
    q2 = _question(number_label="Q2", marks=3.0, confidence=0.6)  # ambiguous: no geometry match
    total = _declared_total("20")
    result = evaluate_marks_and_total([q1, q2], [total])
    assert result.status == AcademicStatus.PARTIALLY_SATISFIED
    assert "Q2" in result.explanation


def test_multiple_ambiguous_marks_on_mismatch_is_not_satisfied() -> None:
    q1 = _question(number_label="Q1", marks=5.0, confidence=0.6)
    q2 = _question(number_label="Q2", marks=3.0, confidence=0.6)
    total = _declared_total("20")
    result = evaluate_marks_and_total([q1, q2], [total])
    assert result.status == AcademicStatus.NOT_SATISFIED


def test_parent_mark_is_authoritative_and_not_double_counted() -> None:
    parent_id = uuid.uuid4()
    top = Question(
        id=parent_id,
        analysis_id=ANALYSIS_ID,
        parent_question_id=None,
        number_label="Q1",
        question_text="Q1 stem",
        page_number=1,
        marks=8.0,
        sequence=1,
        confidence=1.0,
    )
    child_a = _question(number_label="Q1(a)", marks=3.0, parent_id=parent_id)
    child_b = _question(number_label="Q1(b)", marks=4.0, parent_id=parent_id)
    total = _declared_total("8")

    result = evaluate_marks_and_total([top, child_a, child_b], [total])

    assert result.status == AcademicStatus.SATISFIED


def test_parent_mark_allows_children_without_individual_marks() -> None:
    parent_id = uuid.uuid4()
    top = Question(
        id=parent_id,
        analysis_id=ANALYSIS_ID,
        parent_question_id=None,
        number_label="Q2",
        question_text="Question 2 - True or False",
        page_number=1,
        marks=5.0,
        sequence=1,
        confidence=1.0,
    )
    children = [
        _question(number_label=f"Q2.{index}", marks=None, parent_id=parent_id)
        for index in range(1, 6)
    ]
    total = _declared_total("5")

    result = evaluate_marks_and_total([top, *children], [total])

    assert result.status == AcademicStatus.SATISFIED
    assert "could not be read" not in result.explanation


def test_children_are_summed_when_parent_mark_is_missing() -> None:
    parent_id = uuid.uuid4()
    top = Question(
        id=parent_id,
        analysis_id=ANALYSIS_ID,
        parent_question_id=None,
        number_label="Q3",
        question_text="Q3 stem",
        page_number=1,
        marks=None,
        sequence=1,
        confidence=1.0,
    )
    child_a = _question(number_label="Q3(a)", marks=3.0, parent_id=parent_id)
    child_b = _question(number_label="Q3(b)", marks=3.0, parent_id=parent_id)
    child_c = _question(number_label="Q3(c)", marks=2.0, parent_id=parent_id)
    total = _declared_total("8")

    result = evaluate_marks_and_total([top, child_a, child_b, child_c], [total])

    assert result.status == AcademicStatus.SATISFIED


def test_parent_mark_wins_even_when_child_sum_is_greater() -> None:
    parent_id = uuid.uuid4()
    top = Question(
        id=parent_id,
        analysis_id=ANALYSIS_ID,
        parent_question_id=None,
        number_label="Q4",
        question_text="Q4 stem",
        page_number=1,
        marks=8.0,
        sequence=1,
        confidence=1.0,
    )
    child_a = _question(number_label="Q4(a)", marks=5.0, parent_id=parent_id)
    child_b = _question(number_label="Q4(b)", marks=5.0, parent_id=parent_id)
    total = _declared_total("8")

    result = evaluate_marks_and_total([top, child_a, child_b], [total])

    assert result.status == AcademicStatus.SATISFIED


def test_missing_child_mark_blocks_only_when_parent_mark_is_missing() -> None:
    parent_id = uuid.uuid4()
    top = Question(
        id=parent_id,
        analysis_id=ANALYSIS_ID,
        parent_question_id=None,
        number_label="Q5",
        question_text="Q5 stem",
        page_number=1,
        marks=None,
        sequence=1,
        confidence=1.0,
    )
    child_a = _question(number_label="Q5(a)", marks=3.0, parent_id=parent_id)
    child_b = _question(number_label="Q5(b)", marks=None, parent_id=parent_id)
    total = _declared_total("3")

    result = evaluate_marks_and_total([top, child_a, child_b], [total])

    assert result.status == AcademicStatus.NOT_VERIFIED
    assert "Q5(b)" in result.explanation


def test_standalone_top_level_question_without_children_counts_own_marks() -> None:
    q1 = _question(number_label="Q1", marks=6.0)
    total = _declared_total("6")
    result = evaluate_marks_and_total([q1], [total])
    assert result.status == AcademicStatus.SATISFIED


def test_realistic_exam_parent_totals_equal_declared_thirty() -> None:
    questions: list[Question] = []
    for label, marks in (("Q1", 8.0), ("Q2", 5.0), ("Q3", 8.0), ("Q4", 9.0)):
        parent_id = uuid.uuid4()
        questions.append(
            Question(
                id=parent_id,
                analysis_id=ANALYSIS_ID,
                parent_question_id=None,
                number_label=label,
                question_text=f"{label} stem",
                page_number=1,
                marks=marks,
                sequence=len(questions) + 1,
                confidence=1.0,
            )
        )
        child_count = {"Q1": 8, "Q2": 5, "Q3": 3, "Q4": 3}[label]
        for index in range(1, child_count + 1):
            child_marks = None if label == "Q2" else marks / child_count
            questions.append(
                _question(
                    number_label=f"{label}.{index}",
                    marks=child_marks,
                    parent_id=parent_id,
                )
            )

    result = evaluate_marks_and_total(questions, [_declared_total("30")])

    assert result.status == AcademicStatus.SATISFIED
    assert "Calculated total marks (30" in result.explanation
