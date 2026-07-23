import uuid
from decimal import Decimal

from app.core.domain import AcademicStatus, UploadedFileType
from app.models.evidence import Evidence
from app.models.question import Question
from app.services.rules.marks_total import evaluate_marks_and_total
from app.services.rules.numbering import evaluate_numbering
from app.services.rules.scoring import calculate_overall_score

_ANALYSIS_ID = uuid.uuid4()


def test_score_excludes_not_verified_and_not_applicable() -> None:
    result = calculate_overall_score(
        [
            AcademicStatus.SATISFIED,
            AcademicStatus.PARTIALLY_SATISFIED,
            AcademicStatus.NOT_SATISFIED,
            AcademicStatus.NOT_VERIFIED,
            AcademicStatus.NOT_APPLICABLE,
        ]
    )
    assert result.score == Decimal("50.00")
    assert result.denominator == 3


def test_score_returns_insufficient_evidence_for_zero_denominator() -> None:
    result = calculate_overall_score([AcademicStatus.NOT_VERIFIED, AcademicStatus.NOT_APPLICABLE])
    assert result.score is None
    assert result.denominator == 0
    assert result.label == "Insufficient Evidence"


def _question(number_label: str, marks: float | None) -> Question:
    return Question(
        id=uuid.uuid4(),
        analysis_id=_ANALYSIS_ID,
        parent_question_id=None,
        number_label=number_label,
        question_text=f"{number_label} text",
        page_number=1,
        marks=marks,
        sequence=1,
        confidence=1.0,
    )


def _declared_total_evidence(value: str) -> Evidence:
    return Evidence(
        id=uuid.uuid4(),
        analysis_id=_ANALYSIS_ID,
        source_document=UploadedFileType.EXAM,
        evidence_type="declared_total",
        page_number=1,
        item_reference="total",
        extracted_text=f"Total Marks: {value}",
        confidence=1.0,
    )


def test_calculate_overall_score_from_m6_findings_both_satisfied() -> None:
    # Proves calculate_overall_score can consume M6's rule outputs directly -
    # per the approved M6 decisions, this is call-and-test only: no Analysis
    # row exists in this test, and nothing here persists an aggregate score
    # (that remains Milestone 10 scope).
    questions = [_question("Q1", 5.0), _question("Q2", 3.0)]
    marks_result = evaluate_marks_and_total(questions, [_declared_total_evidence("8")])
    numbering_result = evaluate_numbering(questions, [])

    assert marks_result.status == AcademicStatus.SATISFIED
    assert numbering_result.status == AcademicStatus.SATISFIED

    score = calculate_overall_score([marks_result.status, numbering_result.status])
    assert score.score == Decimal("100.00")
    assert score.denominator == 2


def test_calculate_overall_score_from_m6_findings_excludes_not_applicable_and_not_verified() -> (
    None
):
    # Marks/total: no declared total -> Not Applicable (excluded).
    # Numbering: no questions at all -> Not Verified (excluded).
    marks_result = evaluate_marks_and_total([], [])
    numbering_result = evaluate_numbering([], [])

    assert marks_result.status == AcademicStatus.NOT_APPLICABLE
    assert numbering_result.status == AcademicStatus.NOT_VERIFIED

    score = calculate_overall_score([marks_result.status, numbering_result.status])
    assert score.score is None
    assert score.denominator == 0
    assert score.label == "Insufficient Evidence"


# --- M8 correction: scoring/denominator safety --------------------------


def test_removing_unconditional_not_verified_findings_does_not_change_score() -> None:
    # REQ002/RULE002 and REQ008/RULE008 used to always contribute Not
    # Verified before the M8 correction removed them entirely. Not Verified
    # was already excluded from the denominator, so removing those two
    # inputs must leave the score and denominator unchanged.
    base_statuses = [
        AcademicStatus.SATISFIED,
        AcademicStatus.SATISFIED,
        AcademicStatus.PARTIALLY_SATISFIED,
        AcademicStatus.NOT_APPLICABLE,
    ]
    old_behavior_statuses = [
        *base_statuses,
        AcademicStatus.NOT_VERIFIED,  # formerly RULE002
        AcademicStatus.NOT_VERIFIED,  # formerly RULE008
    ]

    old_score = calculate_overall_score(old_behavior_statuses)
    new_score = calculate_overall_score(base_statuses)

    assert old_score.score == new_score.score
    assert old_score.denominator == new_score.denominator


def test_rule006_none_result_contributes_nothing_to_a_status_list() -> None:
    # Mirrors exactly what run_applying_rules does for the 2+ applicable-CLO
    # case: skip persistence (and therefore skip contributing anything to
    # scoring) when the evaluator returns None, rather than substituting an
    # invented fallback status.
    evaluator_results = [AcademicStatus.SATISFIED, None, AcademicStatus.PARTIALLY_SATISFIED]
    statuses = [status for status in evaluator_results if status is not None]

    assert statuses == [AcademicStatus.SATISFIED, AcademicStatus.PARTIALLY_SATISFIED]
    score = calculate_overall_score(statuses)
    assert score.denominator == 2
