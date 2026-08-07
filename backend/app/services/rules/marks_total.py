"""Marks and total arithmetic rule (REQ018 / RULE018 - "Correct Total Marks").

Pure function: takes already-extracted (M4) questions and exam evidence for
one analysis and returns a single RuleFindingResult. Never touches the
database or the filesystem, so it can be unit-tested with plain in-memory
Question/Evidence instances.

Deterministic mapping from the official KB rule row to code, in evaluation
order:
1. Not_Applicable_Condition ("No declared total is provided") - no
   evidence_type="declared_total" row exists at all.
2. Not_Verified_Condition ("One or more required mark values are
   unreadable") - a top-level question branch has neither a readable parent
   mark nor a complete set of readable child marks.
3. Satisfied_Condition ("The calculated total equals the declared total").
4. Partially_Satisfied_Condition ("The difference is attributable to one
   ambiguous extracted mark requiring review") - exactly one mark source
   used in the calculation has low confidence while every other used mark is
   fully confident.
5. Not_Satisfied_Condition ("The calculated total differs from the declared
   total") - any other mismatch.

Mark precedence for a hierarchical question branch:
- When the parent/top-level question has a readable mark, that mark is the
  authoritative value for the branch and child marks are not added again.
- When the parent mark is absent, readable child marks are summed.
- Missing child marks do not block verification when the parent mark exists.

This rule intentionally does not add a separate parent-child consistency
finding. It calculates the official exam total using the declared parent mark
when available, exactly once.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from app.core.domain import AcademicStatus
from app.models.evidence import Evidence
from app.models.question import Question
from app.services.extraction.line_classification import parse_declared_total
from app.services.rules.types import RuleFindingResult

_NOT_APPLICABLE_EXPLANATION = "No declared total marks were found in the exam."


@dataclass(frozen=True)
class _MarkContribution:
    label: str
    value: Decimal
    confidence: float
    evidence_labels: tuple[str, ...]


def _parse_declared_total(text: str) -> Decimal | None:
    value = parse_declared_total(text)
    return Decimal(str(value)) if value is not None else None


def _effective_branch_marks(
    questions: Sequence[Question],
) -> tuple[list[_MarkContribution], list[str]]:
    """Return one effective mark contribution per top-level branch.

    Parent marks take precedence. If a parent has no mark, its direct child
    branches are resolved recursively so nested structures remain supported.
    A branch is missing only when no authoritative parent mark exists and at
    least one required descendant branch cannot be resolved.
    """

    by_id = {question.id: question for question in questions}
    children_by_parent: dict[uuid.UUID, list[Question]] = defaultdict(list)
    for question in questions:
        if question.parent_question_id is not None:
            children_by_parent[question.parent_question_id].append(question)

    for children in children_by_parent.values():
        children.sort(key=lambda question: (question.sequence, question.number_label))

    top_level = [
        question
        for question in questions
        if question.parent_question_id is None or question.parent_question_id not in by_id
    ]
    top_level.sort(key=lambda question: (question.sequence, question.number_label))

    def resolve(question: Question) -> tuple[_MarkContribution | None, list[str]]:
        if question.marks is not None:
            return (
                _MarkContribution(
                    label=question.number_label,
                    value=Decimal(str(question.marks)),
                    confidence=question.confidence,
                    evidence_labels=(question.number_label,),
                ),
                [],
            )

        children = children_by_parent.get(question.id, [])
        if not children:
            return None, [question.number_label]

        child_contributions: list[_MarkContribution] = []
        missing_labels: list[str] = []
        for child in children:
            contribution, missing = resolve(child)
            if contribution is not None:
                child_contributions.append(contribution)
            missing_labels.extend(missing)

        if missing_labels:
            return None, missing_labels

        return (
            _MarkContribution(
                label=question.number_label,
                value=sum(
                    (contribution.value for contribution in child_contributions),
                    start=Decimal("0"),
                ),
                confidence=min(
                    (contribution.confidence for contribution in child_contributions),
                    default=question.confidence,
                ),
                evidence_labels=tuple(
                    label
                    for contribution in child_contributions
                    for label in contribution.evidence_labels
                ),
            ),
            [],
        )

    contributions: list[_MarkContribution] = []
    missing: list[str] = []
    for question in top_level:
        contribution, unresolved = resolve(question)
        if contribution is not None:
            contributions.append(contribution)
        missing.extend(unresolved)

    return contributions, missing


def evaluate_marks_and_total(
    questions: Sequence[Question], evidence: Sequence[Evidence]
) -> RuleFindingResult:
    marks_evidence_by_label = {e.item_reference: e for e in evidence if e.evidence_type == "marks"}
    text_evidence_by_label = {
        e.item_reference: e for e in evidence if e.evidence_type == "question_text"
    }
    declared_total_evidence = next(
        (e for e in evidence if e.evidence_type == "declared_total"), None
    )

    if declared_total_evidence is None:
        return RuleFindingResult(
            status=AcademicStatus.NOT_APPLICABLE,
            explanation=_NOT_APPLICABLE_EXPLANATION,
            confidence=1.0,
            evidence_ids=[],
        )

    declared_total = _parse_declared_total(declared_total_evidence.extracted_text)
    if declared_total is None:
        return RuleFindingResult(
            status=AcademicStatus.NOT_APPLICABLE,
            explanation=_NOT_APPLICABLE_EXPLANATION,
            confidence=declared_total_evidence.confidence,
            evidence_ids=[declared_total_evidence.id],
        )

    contributions, missing = _effective_branch_marks(questions)
    base_evidence_ids: list[uuid.UUID] = [declared_total_evidence.id]
    for contribution in contributions:
        for label in contribution.evidence_labels:
            text_ev = text_evidence_by_label.get(label)
            if text_ev is not None:
                base_evidence_ids.append(text_ev.id)
            marks_ev = marks_evidence_by_label.get(label)
            if marks_ev is not None:
                base_evidence_ids.append(marks_ev.id)

    if missing:
        return RuleFindingResult(
            status=AcademicStatus.NOT_VERIFIED,
            explanation=(
                "One or more required mark values could not be read for: "
                f"{', '.join(missing)}."
            ),
            confidence=min(
                (contribution.confidence for contribution in contributions),
                default=0.0,
            ),
            evidence_ids=base_evidence_ids,
        )

    calculated_total = sum(
        (contribution.value for contribution in contributions), start=Decimal("0")
    )
    confidence = min((contribution.confidence for contribution in contributions), default=1.0)

    if calculated_total == declared_total:
        return RuleFindingResult(
            status=AcademicStatus.SATISFIED,
            explanation=(
                f"Calculated total marks ({calculated_total}) equal the declared "
                f"total marks ({declared_total})."
            ),
            confidence=confidence,
            evidence_ids=base_evidence_ids,
        )

    ambiguous = [contribution for contribution in contributions if contribution.confidence < 1.0]
    if len(ambiguous) == 1:
        return RuleFindingResult(
            status=AcademicStatus.PARTIALLY_SATISFIED,
            explanation=(
                f"Calculated total marks ({calculated_total}) differ from the declared "
                f"total marks ({declared_total}); the difference is attributable to one "
                f"ambiguous extracted mark ({ambiguous[0].label}) requiring review."
            ),
            confidence=confidence,
            evidence_ids=base_evidence_ids,
        )

    return RuleFindingResult(
        status=AcademicStatus.NOT_SATISFIED,
        explanation=(
            f"Calculated total marks ({calculated_total}) differ from the declared "
            f"total marks ({declared_total})."
        ),
        confidence=confidence,
        evidence_ids=base_evidence_ids,
    )
