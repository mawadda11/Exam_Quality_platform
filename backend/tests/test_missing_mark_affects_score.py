from __future__ import annotations

import uuid

from app.core.domain import AcademicStatus, UploadedFileType
from app.models.evidence import Evidence
from app.models.question import Question
from app.services.rules.marks_total import evaluate_marks_and_total

ANALYSIS_ID = uuid.uuid4()


def _question(label: str, marks: float | None, *, parent_id: uuid.UUID | None = None, sequence: int = 1) -> Question:
    return Question(
        id=uuid.uuid4(), analysis_id=ANALYSIS_ID, parent_question_id=parent_id,
        number_label=label, question_text=f"{label} text", page_number=1,
        marks=marks, sequence=sequence, confidence=1.0,
    )


def _evidence(kind: str, label: str, text: str) -> Evidence:
    return Evidence(
        id=uuid.uuid4(), analysis_id=ANALYSIS_ID, source_document=UploadedFileType.EXAM,
        evidence_type=kind, page_number=1, item_reference=label,
        extracted_text=text, confidence=1.0,
    )


def test_confirmed_missing_leaf_mark_is_not_satisfied() -> None:
    q1 = _question("Q1", 5.0, sequence=1)
    q2 = _question("Q2", None, sequence=2)
    total = _evidence("declared_total", "total", "Total Marks: 10")
    q2_text = _evidence("question_text", "Q2", "Q2 text")

    result = evaluate_marks_and_total([q1, q2], [total, q2_text])

    assert result.status == AcademicStatus.NOT_SATISFIED
    assert "Q2" in result.explanation


def test_partial_child_marking_reports_missing_children_before_arithmetic() -> None:
    parent_id = uuid.uuid4()
    parent = _question("Q4", 8.0, sequence=1)
    parent.id = parent_id
    child_a = _question("Q4(a)", 3.0, parent_id=parent_id, sequence=1)
    child_b = _question("Q4(b)", None, parent_id=parent_id, sequence=2)
    child_c = _question("Q4(c)", None, parent_id=parent_id, sequence=3)
    total = _evidence("declared_total", "total", "Total Marks: 25")
    b_text = _evidence("question_text", "Q4(b)", "Q4(b) text")
    c_text = _evidence("question_text", "Q4(c)", "Q4(c) text")

    result = evaluate_marks_and_total([parent, child_a, child_b, child_c], [total, b_text, c_text])

    assert result.status == AcademicStatus.NOT_SATISFIED
    assert "Q4(b)" in result.explanation
    assert "Q4(c)" in result.explanation
    assert "partial child-level marking" in result.explanation
    assert "child marks total 3" not in result.explanation


def test_scored_parent_can_represent_all_unmarked_children() -> None:
    parent_id = uuid.uuid4()
    parent = _question("Q2", 18.0, sequence=1)
    parent.id = parent_id
    children = [
        _question(f"Q2.{index}", None, parent_id=parent_id, sequence=index)
        for index in range(1, 7)
    ]
    total = _evidence("declared_total", "total", "Total Marks: 18")

    result = evaluate_marks_and_total([parent, *children], [total])

    assert result.status == AcademicStatus.SATISFIED


def test_parent_child_mismatch_is_checked_after_all_children_have_marks() -> None:
    parent_id = uuid.uuid4()
    parent = _question("Q4", 8.0, sequence=1)
    parent.id = parent_id
    children = [
        _question("Q4(a)", 3.0, parent_id=parent_id, sequence=1),
        _question("Q4(b)", 3.0, parent_id=parent_id, sequence=2),
        _question("Q4(c)", 3.0, parent_id=parent_id, sequence=3),
    ]
    total = _evidence("declared_total", "total", "Total Marks: 8")

    result = evaluate_marks_and_total([parent, *children], [total])

    assert result.status == AcademicStatus.NOT_SATISFIED
    assert "child marks total 9.0" in result.explanation


def test_unmarked_structural_parent_is_allowed_when_all_leaf_marks_are_complete() -> None:
    parent_id = uuid.uuid4()
    parent = _question("Q3", None, sequence=1)
    parent.id = parent_id
    children = [
        _question("Q3(a)", 3.0, parent_id=parent_id, sequence=1),
        _question("Q3(b)", 3.0, parent_id=parent_id, sequence=2),
        _question("Q3(c)", 2.0, parent_id=parent_id, sequence=3),
    ]
    total = _evidence("declared_total", "total", "Total Marks: 8")

    result = evaluate_marks_and_total([parent, *children], [total])

    assert result.status == AcademicStatus.SATISFIED


if __name__ == "__main__":
    test_confirmed_missing_leaf_mark_is_not_satisfied()
    test_partial_child_marking_reports_missing_children_before_arithmetic()
    test_scored_parent_can_represent_all_unmarked_children()
    test_parent_child_mismatch_is_checked_after_all_children_have_marks()
    test_unmarked_structural_parent_is_allowed_when_all_leaf_marks_are_complete()
    print("MARK POLICY RUNTIME REGRESSION PASSED")
