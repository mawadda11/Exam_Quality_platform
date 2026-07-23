"""Direct, DB-free unit tests for evaluate_clo_relevance,
evaluate_clo_coverage_distribution, and evaluate_out_of_scope_content -
same in-memory approach as test_clo_topic_alignment.py."""

from __future__ import annotations

import uuid

from app.core.domain import AcademicStatus, UploadedFileType
from app.models.clo import Clo
from app.models.evidence import Evidence
from app.models.question import Question
from app.models.topic import Topic
from app.services.rules.semantic_deferred import (
    evaluate_clo_coverage_distribution,
    evaluate_clo_relevance,
    evaluate_out_of_scope_content,
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


def _topic(code: str) -> Topic:
    return Topic(
        id=uuid.uuid4(),
        analysis_id=ANALYSIS_ID,
        code=code,
        text=f"{code} text",
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


# --- CLO Relevance (REQ002) --------------------------------------------------


def test_clo_relevance_is_always_not_verified() -> None:
    q1 = _question("Q1", "Explain X. [CLO1]")
    clo1 = _clo("CLO1")
    result = evaluate_clo_relevance([q1], [_text_evidence(q1), _clo_evidence(clo1)], [clo1])
    assert result.status == AcademicStatus.NOT_VERIFIED
    assert "semantic" in result.explanation.lower()


def test_clo_relevance_never_returns_satisfied_partial_or_not_satisfied() -> None:
    q1 = _question("Q1", "Explain X. [CLO1]")
    clo1 = _clo("CLO1")
    for questions, evidence, clos in [
        ([], [], []),
        ([q1], [_text_evidence(q1), _clo_evidence(clo1)], [clo1]),
    ]:
        result = evaluate_clo_relevance(questions, evidence, clos)
        assert result.status == AcademicStatus.NOT_VERIFIED


def test_clo_relevance_links_existing_question_and_clo_evidence() -> None:
    q1 = _question("Q1", "Explain X. [CLO1]")
    clo1 = _clo("CLO1")
    text_ev, clo_ev = _text_evidence(q1), _clo_evidence(clo1)
    result = evaluate_clo_relevance([q1], [text_ev, clo_ev], [clo1])
    assert set(result.evidence_ids) == {text_ev.id, clo_ev.id}


# --- Out-of-Scope Content (REQ008) -------------------------------------------


def test_out_of_scope_content_is_always_not_verified() -> None:
    q1 = _question("Q1", "Explain X. [T1]")
    topic1 = _topic("T1")
    result = evaluate_out_of_scope_content(
        [q1], [_text_evidence(q1), _topic_evidence(topic1)], [topic1]
    )
    assert result.status == AcademicStatus.NOT_VERIFIED
    assert "semantic" in result.explanation.lower()


def test_out_of_scope_content_links_existing_question_and_topic_evidence() -> None:
    q1 = _question("Q1", "Explain X. [T1]")
    topic1 = _topic("T1")
    text_ev, topic_ev = _text_evidence(q1), _topic_evidence(topic1)
    result = evaluate_out_of_scope_content([q1], [text_ev, topic_ev], [topic1])
    assert set(result.evidence_ids) == {text_ev.id, topic_ev.id}


# --- CLO Coverage Distribution (REQ006) --------------------------------------


def test_coverage_distribution_single_clo_is_not_applicable() -> None:
    clo1 = _clo("CLO1")
    result = evaluate_clo_coverage_distribution([], [_clo_evidence(clo1)], [clo1])
    assert result.status == AcademicStatus.NOT_APPLICABLE
    assert "one clo" in result.explanation.lower()


def test_coverage_distribution_zero_clos_is_not_verified() -> None:
    result = evaluate_clo_coverage_distribution([], [], [])
    assert result.status == AcademicStatus.NOT_VERIFIED


def test_coverage_distribution_multiple_clos_is_not_verified() -> None:
    q1 = _question("Q1", "Explain X. [CLO1]")
    clo1, clo2 = _clo("CLO1"), _clo("CLO2")
    result = evaluate_clo_coverage_distribution(
        [q1], [_text_evidence(q1), _clo_evidence(clo1), _clo_evidence(clo2)], [clo1, clo2]
    )
    assert result.status == AcademicStatus.NOT_VERIFIED
    assert "threshold" in result.explanation.lower()


def test_coverage_distribution_never_returns_satisfied_partial_or_not_satisfied() -> None:
    q1 = _question("Q1", "Explain X.")
    clo1, clo2 = _clo("CLO1"), _clo("CLO2")
    for questions, evidence, clos in [
        ([], [_clo_evidence(clo1)], [clo1]),  # Not Applicable case
        ([], [], []),
        ([q1], [_text_evidence(q1), _clo_evidence(clo1), _clo_evidence(clo2)], [clo1, clo2]),
    ]:
        result = evaluate_clo_coverage_distribution(questions, evidence, clos)
        assert result.status in (AcademicStatus.NOT_APPLICABLE, AcademicStatus.NOT_VERIFIED)


def test_coverage_distribution_single_clo_links_only_that_clos_evidence() -> None:
    clo1 = _clo("CLO1")
    clo1_ev = _clo_evidence(clo1)
    result = evaluate_clo_coverage_distribution([], [clo1_ev], [clo1])
    assert result.evidence_ids == [clo1_ev.id]
