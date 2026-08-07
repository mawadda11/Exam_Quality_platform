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
    evaluate_clo_coverage_distribution,
)

ANALYSIS_ID = uuid.uuid4()


def _question(
    number_label: str,
    text: str,
    parent_question_id: uuid.UUID | None = None,
) -> Question:
    return Question(
        id=uuid.uuid4(),
        analysis_id=ANALYSIS_ID,
        parent_question_id=parent_question_id,
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


def test_structural_parent_is_excluded_while_child_coverage_is_evaluated() -> None:
    parent = _question("Q1", "Answer both parts.")
    child = _question("Q1(a)", "About X. [CLO1]", parent_question_id=parent.id)
    clo = _clo("CLO1")
    parent_evidence = _text_evidence(parent)
    child_evidence = _text_evidence(child)
    clo_evidence = _clo_evidence(clo)

    result = evaluate_applicable_clo_coverage(
        [parent, child],
        [parent_evidence, child_evidence, clo_evidence],
        [clo],
    )

    assert result.status == AcademicStatus.SATISFIED
    assert child_evidence.id in result.evidence_ids
    assert parent_evidence.id not in result.evidence_ids


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


# --- CLO Coverage Distribution (REQ006) - M8 correction ---------------------
#
# Only genuinely deterministic for 0 or 1 applicable CLOs. For 2+, no
# concentration threshold exists in the KB, so the function returns None
# rather than an unconditional Not Verified Finding - see
# app.services.rules.capability_manifest for how that gap is documented.


def test_coverage_distribution_zero_clos_is_not_verified() -> None:
    result = evaluate_clo_coverage_distribution([], [])
    assert result is not None
    assert result.status == AcademicStatus.NOT_VERIFIED


def test_coverage_distribution_single_clo_is_not_applicable() -> None:
    clo1 = _clo("CLO1")
    clo1_ev = _clo_evidence(clo1)
    result = evaluate_clo_coverage_distribution([clo1_ev], [clo1])
    assert result is not None
    assert result.status == AcademicStatus.NOT_APPLICABLE
    assert "one clo" in result.explanation.lower()
    assert result.evidence_ids == [clo1_ev.id]


def test_coverage_distribution_two_clos_returns_none() -> None:
    clo1, clo2 = _clo("CLO1"), _clo("CLO2")
    result = evaluate_clo_coverage_distribution(
        [_clo_evidence(clo1), _clo_evidence(clo2)], [clo1, clo2]
    )
    assert result is None


def test_coverage_distribution_many_clos_returns_none() -> None:
    clos = [_clo(f"CLO{i}") for i in range(1, 6)]
    evidence = [_clo_evidence(clo) for clo in clos]
    result = evaluate_clo_coverage_distribution(evidence, clos)
    assert result is None


def test_coverage_distribution_never_returns_satisfied_partial_or_not_satisfied() -> None:
    clo1 = _clo("CLO1")
    for evidence, clos in [
        ([], []),
        ([_clo_evidence(clo1)], [clo1]),
    ]:
        result = evaluate_clo_coverage_distribution(evidence, clos)
        assert result is not None
        assert result.status in (AcademicStatus.NOT_APPLICABLE, AcademicStatus.NOT_VERIFIED)


# --- M7 semantic relationship aggregation -----------------------------------


def _semantic_mapping(
    *,
    rule_id: str,
    requirement_id: str,
    rule_name: str,
    source: Evidence,
    targets: list[Evidence],
    status: AcademicStatus,
    item_status: AcademicStatus,
    selected_targets: list[Evidence],
):
    from app.core.domain import SemanticConfidenceLevel
    from app.services.rules.identifiers import RuleIdentifier
    from app.services.rules.semantic_evaluators import SemanticRuleEvaluation
    from app.services.rules.semantic_types import SemanticItemJudgment

    cited = [source.id, *(item.id for item in selected_targets)]
    return SemanticRuleEvaluation(
        identifier=RuleIdentifier(requirement_id, rule_id, rule_name),
        status=status,
        confidence_level=SemanticConfidenceLevel.HIGH,
        confidence=1.0,
        evidence_ids=cited,
        explanation="Validated semantic mapping.",
        recommendation_id=None,
        evaluator_type="local_semantic_baseline",
        provider="local",
        model="local-governed-baseline-v1",
        prompt_template_version="test",
        kb_version="1.0.0",
        items=(
            SemanticItemJudgment(
                source_evidence_id=source.id,
                target_evidence_ids=[item.id for item in selected_targets],
                status=item_status,
                reasoning="Evidence-grounded mapping.",
            ),
        ),
        confidence_basis=("Complete source coverage.",),
    )


def test_semantic_clo_coverage_uses_validated_relationships_without_code_citations() -> None:
    from app.services.rules.clo_topic_coverage import (
        evaluate_applicable_clo_coverage_from_relationships,
    )

    question = _question("Q1", "Explain cohesion and coupling.")
    source = _text_evidence(question)
    clo = _clo("CLO1")
    target = _clo_evidence(clo)
    mapping = _semantic_mapping(
        rule_id="RULE001",
        requirement_id="REQ001",
        rule_name="Question-to-CLO Mapping",
        source=source,
        targets=[target],
        status=AcademicStatus.SATISFIED,
        item_status=AcademicStatus.SATISFIED,
        selected_targets=[target],
    )

    result = evaluate_applicable_clo_coverage_from_relationships([source, target], mapping)

    assert result.status is AcademicStatus.SATISFIED
    assert set(result.evidence_ids) == {source.id, target.id}


def test_local_semantic_coverage_keeps_missing_target_not_verified() -> None:
    from app.services.rules.clo_topic_coverage import (
        evaluate_applicable_clo_coverage_from_relationships,
    )

    question = _question("Q1", "Explain cohesion.")
    source = _text_evidence(question)
    first = _clo_evidence(_clo("CLO1"))
    second = _clo_evidence(_clo("CLO2"))
    mapping = _semantic_mapping(
        rule_id="RULE001",
        requirement_id="REQ001",
        rule_name="Question-to-CLO Mapping",
        source=source,
        targets=[first, second],
        status=AcademicStatus.SATISFIED,
        item_status=AcademicStatus.SATISFIED,
        selected_targets=[first],
    )

    result = evaluate_applicable_clo_coverage_from_relationships([source, first, second], mapping)

    assert result.status is AcademicStatus.NOT_VERIFIED
    assert "CLO2" in result.explanation
    assert "local-only semantic baseline" in result.explanation
    assert second.id in result.evidence_ids


def test_semantic_coverage_preserves_limited_support_as_partial() -> None:
    from app.services.rules.clo_topic_coverage import (
        evaluate_applicable_topic_coverage_from_relationships,
    )

    question = _question("Q1", "Discuss a related design topic.")
    source = _text_evidence(question)
    target = _topic_evidence(_topic("T1"))
    mapping = _semantic_mapping(
        rule_id="RULE007",
        requirement_id="REQ007",
        rule_name="Question-to-Topic Alignment",
        source=source,
        targets=[target],
        status=AcademicStatus.PARTIALLY_SATISFIED,
        item_status=AcademicStatus.PARTIALLY_SATISFIED,
        selected_targets=[target],
    )

    result = evaluate_applicable_topic_coverage_from_relationships([source, target], mapping)

    assert result.status is AcademicStatus.PARTIALLY_SATISFIED
    assert "limited" in result.explanation.lower()
