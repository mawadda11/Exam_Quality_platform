from __future__ import annotations

from app.core.domain import QuestionReviewStatus, QuestionType
from app.services.extraction.structure_reconciliation import reconcile_structure_candidates
from app.services.extraction.types import ExtractedQuestion, Geometry


def _question(*, text: str, ids: tuple[str, ...], confidence: float = 1.0) -> ExtractedQuestion:
    return ExtractedQuestion(
        number_label="Q5",
        text=text,
        page_number=1,
        parent_number_label=None,
        marks=6.0,
        sequence=5,
        confidence=confidence,
        geometry=Geometry(10, 10, 500, 30 if len(ids) > 1 else 18),
        local_key="q5-local",
        question_type=QuestionType.SHORT_ANSWER,
        source_line_ids=ids,
    )


def test_reconciliation_promotes_visual_source_superset_for_truncated_local_stem() -> None:
    first = (
        "A queue initially contains A, B, and C, with A at the front. "
        "Perform the operations enqueue(D),"
    )
    second = "dequeue(), enqueue(E), and dequeue(). Show the queue after each operation."
    local = _question(text=first, ids=("P1-L1",), confidence=1.0)
    visual = _question(text=f"{first} {second}", ids=("P1-L1", "P1-L2"), confidence=0.98)

    result = reconcile_structure_candidates(
        local_questions=(local,),
        visual_questions=(visual,),
        local_candidates=(),
        visual_candidates=(),
    )

    question = result.questions[0]
    assert question.text == f"{first} {second}"
    assert question.source_line_ids == ("P1-L1", "P1-L2")
    assert question.confidence == 0.95
    assert question.review_status is QuestionReviewStatus.NEEDS_REVIEW
    assert any(w.code == "QUESTION_BOUNDARY_MISMATCH" for w in result.warnings)


def test_reconciliation_does_not_append_unrelated_nearby_text_even_with_source_superset() -> None:
    local_text = "Question 5: Explain the queue operation."
    local = _question(text=local_text, ids=("P1-L1",))
    visual = _question(
        text=f"{local_text} Department watermark text",
        ids=("P1-L1", "P1-L2"),
        confidence=0.99,
    )

    result = reconcile_structure_candidates(
        local_questions=(local,),
        visual_questions=(visual,),
        local_candidates=(),
        visual_candidates=(),
    )

    question = result.questions[0]
    assert question.text == local_text
    assert question.source_line_ids == ("P1-L1",)
    assert any(w.code == "QUESTION_BOUNDARY_MISMATCH" for w in result.warnings)
