from __future__ import annotations

import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.domain import AcademicStatus, UploadedFileType
from app.models.evidence import Evidence
from app.models.question import Question
from app.services.rules.marks_total import evaluate_marks_and_total

ANALYSIS_ID = uuid.uuid4()


def _q(label: str, marks: float | None, *, parent_id: uuid.UUID | None = None, seq: int = 1) -> Question:
    return Question(
        id=uuid.uuid4(), analysis_id=ANALYSIS_ID, parent_question_id=parent_id,
        number_label=label, question_text=f"{label} text", page_number=1,
        marks=marks, sequence=seq, confidence=1.0,
    )


def _total(value: str) -> Evidence:
    return Evidence(
        id=uuid.uuid4(), analysis_id=ANALYSIS_ID,
        source_document=UploadedFileType.EXAM,
        evidence_type="declared_total", page_number=1,
        item_reference="total", extracted_text=f"Total Marks: {value}",
        confidence=1.0,
    )


def main() -> None:
    # 1) All child marks absent + scored parent -> valid section-level marking.
    parent = _q("Q2", 18.0)
    children = [_q(f"Q2.{i}", None, parent_id=parent.id, seq=i) for i in range(1, 7)]
    result = evaluate_marks_and_total([parent, *children], [_total("18")])
    assert result.status == AcademicStatus.SATISFIED, result.explanation

    # 2) Partial child marking -> report exactly the missing children first.
    parent = _q("Q4", 8.0)
    children = [
        _q("Q4(a)", 3.0, parent_id=parent.id, seq=1),
        _q("Q4(b)", None, parent_id=parent.id, seq=2),
        _q("Q4(c)", None, parent_id=parent.id, seq=3),
    ]
    result = evaluate_marks_and_total([parent, *children], [_total("8")])
    assert result.status == AcademicStatus.NOT_SATISFIED, result.explanation
    assert "Q4(b)" in result.explanation and "Q4(c)" in result.explanation, result.explanation
    assert "child marks total 3" not in result.explanation, result.explanation

    # 3) All child marks present -> compare complete child total with parent.
    parent = _q("Q4", 8.0)
    children = [
        _q("Q4(a)", 3.0, parent_id=parent.id, seq=1),
        _q("Q4(b)", 3.0, parent_id=parent.id, seq=2),
        _q("Q4(c)", 3.0, parent_id=parent.id, seq=3),
    ]
    result = evaluate_marks_and_total([parent, *children], [_total("8")])
    assert result.status == AcademicStatus.NOT_SATISFIED, result.explanation
    assert "child marks total 9.0" in result.explanation, result.explanation

    # 4) Standalone missing mark remains a real failure.
    q1 = _q("Q1", 5.0, seq=1)
    q2 = _q("Q2", None, seq=2)
    result = evaluate_marks_and_total([q1, q2], [_total("10")])
    assert result.status == AcademicStatus.NOT_SATISFIED, result.explanation
    assert "Q2" in result.explanation, result.explanation

    # 5) Unscored parent cannot hide an unresolved child mark.
    parent = _q("Q3", None)
    children = [
        _q("Q3(a)", 3.0, parent_id=parent.id, seq=1),
        _q("Q3(b)", None, parent_id=parent.id, seq=2),
    ]
    result = evaluate_marks_and_total([parent, *children], [_total("3")])
    assert result.status == AcademicStatus.NOT_SATISFIED, result.explanation
    assert "Q3(b)" in result.explanation, result.explanation

    print("SECTION-LEVEL MARK POLICY RUNTIME REGRESSION PASSED (5/5)")


if __name__ == "__main__":
    main()
