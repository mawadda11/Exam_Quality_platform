"""Direct, DB-free unit tests for evaluate_question_to_clo_mapping and
evaluate_question_to_topic_alignment - same in-memory approach as
test_rules_marks_total.py."""

from __future__ import annotations

import uuid

from app.core.domain import AcademicStatus, UploadedFileType
from app.models.clo import Clo
from app.models.evidence import Evidence
from app.models.question import Question
from app.models.topic import Topic
from app.services.rules.clo_topic_alignment import (
    evaluate_question_to_clo_mapping,
    evaluate_question_to_topic_alignment,
)

ANALYSIS_ID = uuid.uuid4()


def _question(number_label: str, text: str, confidence: float = 1.0) -> Question:
    return Question(
        id=uuid.uuid4(),
        analysis_id=ANALYSIS_ID,
        parent_question_id=None,
        number_label=number_label,
        question_text=text,
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


# --- Question-to-CLO mapping (REQ001) ---------------------------------------


def test_no_questions_is_not_verified() -> None:
    result = evaluate_question_to_clo_mapping([], [], [_clo("CLO1")])
    assert result.status == AcademicStatus.NOT_VERIFIED


def test_no_clos_is_not_verified() -> None:
    q1 = _question("Q1", "Explain something. [CLO1]")
    result = evaluate_question_to_clo_mapping([q1], [_text_evidence(q1)], [])
    assert result.status == AcademicStatus.NOT_VERIFIED


def test_all_questions_cited_is_satisfied() -> None:
    q1 = _question("Q1", "Explain X. [CLO1]")
    q2 = _question("Q2", "Explain Y. [CLO2]")
    clo1, clo2 = _clo("CLO1"), _clo("CLO2")
    evidence = [_text_evidence(q1), _text_evidence(q2), _clo_evidence(clo1), _clo_evidence(clo2)]

    result = evaluate_question_to_clo_mapping([q1, q2], evidence, [clo1, clo2])

    assert result.status == AcademicStatus.SATISFIED
    assert set(result.evidence_ids) == {e.id for e in evidence}


def test_no_questions_cited_is_not_verified() -> None:
    # Absence of a citation does not prove non-alignment - it must be
    # reported as Not Verified, never downgraded to Not Satisfied.
    q1 = _question("Q1", "Explain X with no citation.")
    result = evaluate_question_to_clo_mapping([q1], [_text_evidence(q1)], [_clo("CLO1")])
    assert result.status == AcademicStatus.NOT_VERIFIED


def test_some_questions_cited_is_partially_satisfied() -> None:
    q1 = _question("Q1", "Explain X. [CLO1]")
    q2 = _question("Q2", "Explain Y with no citation.")
    clo1 = _clo("CLO1")
    result = evaluate_question_to_clo_mapping(
        [q1, q2], [_text_evidence(q1), _text_evidence(q2), _clo_evidence(clo1)], [clo1]
    )
    assert result.status == AcademicStatus.PARTIALLY_SATISFIED
    assert "Q2" in result.explanation


def test_clo_mapping_never_returns_not_applicable_or_not_satisfied() -> None:
    # REQ001's KB row declares Not_Applicable_Condition "None"; Not
    # Satisfied is never reachable by this heuristic at all (see module
    # docstring - absence of a citation is Not Verified, not a disproof).
    q1 = _question("Q1", "no citation")
    q2 = _question("Q2", "no citation either")
    clo1 = _clo("CLO1")
    for questions, evidence, clos in [
        ([], [], []),
        ([q1], [], [clo1]),
        ([q1, q2], [_text_evidence(q1), _text_evidence(q2), _clo_evidence(clo1)], [clo1]),
    ]:
        result = evaluate_question_to_clo_mapping(questions, evidence, clos)
        assert result.status not in (AcademicStatus.NOT_APPLICABLE, AcademicStatus.NOT_SATISFIED)


# --- Question-to-topic alignment (REQ007) -----------------------------------


def test_topic_alignment_no_topics_is_not_verified() -> None:
    q1 = _question("Q1", "Explain X. [T1]")
    result = evaluate_question_to_topic_alignment([q1], [_text_evidence(q1)], [])
    assert result.status == AcademicStatus.NOT_VERIFIED


def test_topic_alignment_all_cited_is_satisfied() -> None:
    q1 = _question("Q1", "Explain X. [T1]")
    topic1 = _topic("T1")
    result = evaluate_question_to_topic_alignment(
        [q1], [_text_evidence(q1), _topic_evidence(topic1)], [topic1]
    )
    assert result.status == AcademicStatus.SATISFIED


def test_topic_alignment_none_cited_is_not_verified() -> None:
    q1 = _question("Q1", "Explain X with no citation.")
    result = evaluate_question_to_topic_alignment([q1], [_text_evidence(q1)], [_topic("T1")])
    assert result.status == AcademicStatus.NOT_VERIFIED


def test_topic_alignment_skips_topics_with_no_code() -> None:
    # A topic with no parseable code can never be cited - it is simply
    # excluded from the searchable set, it does not block evaluation.
    q1 = _question("Q1", "Explain X. [T1]")
    topic1 = _topic("T1")
    topic_uncoded = _topic(None)
    result = evaluate_question_to_topic_alignment(
        [q1], [_text_evidence(q1), _topic_evidence(topic1)], [topic1, topic_uncoded]
    )
    assert result.status == AcademicStatus.SATISFIED
