"""Direct, DB-free unit tests for evaluate_applicable_clo_coverage and
evaluate_applicable_topic_coverage - same in-memory approach as
test_clo_topic_alignment.py."""

from __future__ import annotations

import uuid

from app.core.domain import AcademicStatus, UploadedFileType
from app.models.clo import Clo
from app.models.evidence import Evidence
from app.models.question import Question
from app.models.topic import Topic
from app.services.rules.clo_topic_coverage import (
    evaluate_applicable_clo_coverage,
    evaluate_applicable_topic_coverage,
)

ANALYSIS_ID = uuid.uuid4()


def _question(number_label: str, text: str) -> Question:
    return Question(
        id=uuid.uuid4(),
        analysis_id=ANALYSIS_ID,
        parent_question_id=None,
        number_label=number_label,
        question_text=text,
        page_number=1,
        marks=None,
        sequence=1,
        confidence=1.0,
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


def _clo(code: str) -> Clo:
    return Clo(
        id=uuid.uuid4(),
        analysis_id=ANALYSIS_ID,
        code=code,
        text=f"{code} text",
        program_outcome_reference=None,
        page_number=1,
        confidence=1.0,
    )


def _topic(code: str | None) -> Topic:
    return Topic(
        id=uuid.uuid4(),
        analysis_id=ANALYSIS_ID,
        code=code,
        text=f"{code or 'untitled'} text",
        expected_hours=None,
        page_number=1,
        confidence=1.0,
    )


def _clo_evidence(clo: Clo) -> Evidence:
    return Evidence(
        id=uuid.uuid4(),
        analysis_id=ANALYSIS_ID,
        source_document=UploadedFileType.TP153,
        evidence_type="clo",
        page_number=1,
        item_reference=clo.code,
        extracted_text=clo.text,
        confidence=1.0,
    )


def _topic_evidence(topic: Topic) -> Evidence:
    assert topic.code is not None
    return Evidence(
        id=uuid.uuid4(),
        analysis_id=ANALYSIS_ID,
        source_document=UploadedFileType.TP153,
        evidence_type="topic",
        page_number=1,
        item_reference=topic.code,
        extracted_text=topic.text,
        confidence=1.0,
    )


# --- Applicable CLO coverage (REQ005) ---------------------------------------


def test_clo_coverage_no_questions_is_not_verified() -> None:
    result = evaluate_applicable_clo_coverage([], [], [_clo("CLO1")])
    assert result.status == AcademicStatus.NOT_VERIFIED


def test_clo_coverage_no_clos_is_not_verified() -> None:
    q1 = _question("Q1", "no citation")
    result = evaluate_applicable_clo_coverage([q1], [_text_evidence(q1)], [])
    assert result.status == AcademicStatus.NOT_VERIFIED


def test_clo_coverage_all_covered_is_satisfied() -> None:
    q1 = _question("Q1", "About X. [CLO1]")
    q2 = _question("Q2", "About Y. [CLO2]")
    clo1, clo2 = _clo("CLO1"), _clo("CLO2")
    evidence = [_text_evidence(q1), _text_evidence(q2), _clo_evidence(clo1), _clo_evidence(clo2)]

    result = evaluate_applicable_clo_coverage([q1, q2], evidence, [clo1, clo2])

    assert result.status == AcademicStatus.SATISFIED
    assert set(result.evidence_ids) == {e.id for e in evidence}


def test_clo_coverage_some_covered_is_partially_satisfied() -> None:
    q1 = _question("Q1", "About X. [CLO1]")
    clo1, clo2 = _clo("CLO1"), _clo("CLO2")  # CLO2 never cited
    result = evaluate_applicable_clo_coverage(
        [q1], [_text_evidence(q1), _clo_evidence(clo1), _clo_evidence(clo2)], [clo1, clo2]
    )
    assert result.status == AcademicStatus.PARTIALLY_SATISFIED
    assert "CLO2" in result.explanation


def test_clo_coverage_none_covered_is_not_verified() -> None:
    # Zero citations for any applicable CLO does not prove non-coverage -
    # it must be reported as Not Verified, never downgraded to Not Satisfied.
    q1 = _question("Q1", "No citation here.")
    clo1, clo2 = _clo("CLO1"), _clo("CLO2")
    result = evaluate_applicable_clo_coverage(
        [q1], [_text_evidence(q1), _clo_evidence(clo1), _clo_evidence(clo2)], [clo1, clo2]
    )
    assert result.status == AcademicStatus.NOT_VERIFIED


def test_clo_coverage_never_returns_not_applicable_or_not_satisfied() -> None:
    # REQ005's KB row declares Not_Applicable_Condition "None"; Not
    # Satisfied is never reachable by this heuristic at all.
    q1 = _question("Q1", "No citation here.")
    clo1 = _clo("CLO1")
    for questions, evidence, clos in [
        ([], [], []),
        ([q1], [_text_evidence(q1), _clo_evidence(clo1)], [clo1]),
    ]:
        result = evaluate_applicable_clo_coverage(questions, evidence, clos)
        assert result.status not in (AcademicStatus.NOT_APPLICABLE, AcademicStatus.NOT_SATISFIED)


# --- Applicable topic coverage (REQ009) -------------------------------------


def test_topic_coverage_no_topics_is_not_applicable() -> None:
    q1 = _question("Q1", "no citation")
    result = evaluate_applicable_topic_coverage([q1], [_text_evidence(q1)], [])
    assert result.status == AcademicStatus.NOT_APPLICABLE


def test_topic_coverage_uncoded_topic_is_not_verified() -> None:
    q1 = _question("Q1", "About X. [T1]")
    topic1 = _topic("T1")
    topic_uncoded = _topic(None)
    result = evaluate_applicable_topic_coverage(
        [q1], [_text_evidence(q1), _topic_evidence(topic1)], [topic1, topic_uncoded]
    )
    assert result.status == AcademicStatus.NOT_VERIFIED


def test_topic_coverage_all_covered_is_satisfied() -> None:
    q1 = _question("Q1", "About X. [T1]")
    topic1 = _topic("T1")
    result = evaluate_applicable_topic_coverage(
        [q1], [_text_evidence(q1), _topic_evidence(topic1)], [topic1]
    )
    assert result.status == AcademicStatus.SATISFIED


def test_topic_coverage_some_covered_is_partially_satisfied() -> None:
    q1 = _question("Q1", "About X. [T1]")
    topic1, topic2 = _topic("T1"), _topic("T2")
    result = evaluate_applicable_topic_coverage(
        [q1],
        [_text_evidence(q1), _topic_evidence(topic1), _topic_evidence(topic2)],
        [topic1, topic2],
    )
    assert result.status == AcademicStatus.PARTIALLY_SATISFIED
    assert "T2" in result.explanation


def test_topic_coverage_none_covered_is_not_verified() -> None:
    q1 = _question("Q1", "No citation here.")
    topic1, topic2 = _topic("T1"), _topic("T2")
    result = evaluate_applicable_topic_coverage(
        [q1],
        [_text_evidence(q1), _topic_evidence(topic1), _topic_evidence(topic2)],
        [topic1, topic2],
    )
    assert result.status == AcademicStatus.NOT_VERIFIED
