from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import replace

from app.core.domain import (
    AcademicStatus,
    ReferenceResolutionStatus,
    ReferenceTargetType,
    SemanticConfidenceLevel,
)
from app.models.evidence import Evidence
from app.schemas.extraction_review import ExtractionReviewSnapshot
from app.services.rules.semantic_evaluators import SemanticRuleEvaluation


def _states(snapshot: ExtractionReviewSnapshot):
    result = defaultdict(set)
    for ref in snapshot.document_references:
        if (
            ref.included
            and ref.question_source_record_id
            and ref.target_type is not ReferenceTargetType.QUESTION
            # Contextual/deictic references (for example "the diagram below")
            # remain visible for faculty review, but they are intentionally
            # outside automatic scoring and must not gate semantic judgments.
            and not getattr(ref, "normalized_target_label", "").endswith(":unlabeled")
        ):
            result[ref.question_source_record_id].add(ref.resolution_status)
    return result


def _question_by_evidence(evidence: Sequence[Evidence]):
    return {
        item.id: item.question_id
        for item in evidence
        if item.question_id is not None and item.evidence_type == "question_text"
    }


def _aggregate_with_local_uncertainty(
    evaluation: SemanticRuleEvaluation,
    *,
    items: tuple,
    explanation: str,
) -> SemanticRuleEvaluation:
    """Keep reference uncertainty local instead of invalidating the whole rule.

    A missing/ambiguous supporting item can make *that question* unjudgeable,
    but other question-level judgments remain usable.  The whole rule becomes
    Not Verified only when no question remains judgeable.  Otherwise the rule
    is Partially Satisfied unless the remaining verified evidence is uniformly
    negative.
    """

    judged = [item for item in items if item.status is not AcademicStatus.NOT_VERIFIED]
    if not judged:
        return replace(
            evaluation,
            status=AcademicStatus.NOT_VERIFIED,
            confidence_level=SemanticConfidenceLevel.LOW,
            confidence=0.0,
            explanation=explanation,
            recommendation_id=None,
            items=items,
            confidence_basis=tuple(
                dict.fromkeys(
                    [*evaluation.confidence_basis, "supporting_reference_dependency"]
                )
            ),
        )

    judged_statuses = {item.status for item in judged}
    if judged_statuses == {AcademicStatus.NOT_SATISFIED}:
        status = AcademicStatus.NOT_SATISFIED
    else:
        # Some questions were evaluated and some were locally excluded, so a
        # partial exam-level judgment is more informative than discarding the
        # entire rule from the score.
        status = AcademicStatus.PARTIALLY_SATISFIED

    return replace(
        evaluation,
        status=status,
        explanation=explanation,
        recommendation_id=None,
        items=items,
        confidence_basis=tuple(
            dict.fromkeys([*evaluation.confidence_basis, "supporting_reference_dependency"])
        ),
    )


def gate_relationship(
    evaluation: SemanticRuleEvaluation,
    evidence: Sequence[Evidence],
    snapshot: ExtractionReviewSnapshot,
) -> SemanticRuleEvaluation:
    states = _states(snapshot)
    question_map = _question_by_evidence(evidence)
    changed = False
    items = []

    for item in evaluation.items:
        question_id = question_map.get(item.source_evidence_id)
        reference_states = states.get(question_id, set())
        if (
            ReferenceResolutionStatus.UNRESOLVED in reference_states
            or ReferenceResolutionStatus.AMBIGUOUS in reference_states
        ):
            changed = True
            reason = (
                "This question depends on required supporting material that is missing."
                if ReferenceResolutionStatus.UNRESOLVED in reference_states
                else "This question depends on supporting material whose target is ambiguous."
            )
            items.append(
                item.model_copy(
                    update={
                        "status": AcademicStatus.NOT_VERIFIED,
                        "target_evidence_ids": [],
                        "reasoning": reason,
                    }
                )
            )
        else:
            items.append(item)

    if not changed:
        return evaluation

    return _aggregate_with_local_uncertainty(
        evaluation,
        items=tuple(items),
        explanation=(
            "Some question-level relationships could not be judged because their required "
            "supporting material is missing or ambiguous; the remaining confirmed "
            "relationships were still evaluated."
        ),
    )


def gate_complete_information(
    evaluation: SemanticRuleEvaluation,
    evidence: Sequence[Evidence],
    snapshot: ExtractionReviewSnapshot,
) -> SemanticRuleEvaluation:
    states = _states(snapshot)
    question_map = _question_by_evidence(evidence)
    missing = False
    ambiguous = False
    items = []

    for item in evaluation.items:
        question_id = question_map.get(item.source_evidence_id)
        reference_states = states.get(question_id, set())
        if ReferenceResolutionStatus.UNRESOLVED in reference_states:
            missing = True
            items.append(
                item.model_copy(
                    update={
                        "status": AcademicStatus.NOT_SATISFIED,
                        "reasoning": (
                            "The question depends on required supporting material that is missing."
                        ),
                    }
                )
            )
        elif ReferenceResolutionStatus.AMBIGUOUS in reference_states:
            ambiguous = True
            items.append(
                item.model_copy(
                    update={
                        "status": AcademicStatus.PARTIALLY_SATISFIED,
                        "reasoning": (
                            "Required supporting material is present, but the intended target "
                            "is not uniquely identified."
                        ),
                    }
                )
            )
        else:
            items.append(item)

    if not missing and not ambiguous:
        return evaluation

    if missing:
        status = AcademicStatus.NOT_SATISFIED
        explanation = "At least one question lacks required supporting material."
    else:
        status = AcademicStatus.PARTIALLY_SATISFIED
        explanation = (
            "Required supporting material is present, but at least one question refers to "
            "an ambiguous target."
        )

    return replace(
        evaluation,
        status=status,
        explanation=explanation,
        recommendation_id=None,
        items=tuple(items),
        confidence_basis=tuple(
            dict.fromkeys([*evaluation.confidence_basis, "supporting_reference_dependency"])
        ),
    )
