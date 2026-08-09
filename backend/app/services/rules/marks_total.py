"""Marks and total arithmetic rule (REQ018 / RULE018 - "Correct Total Marks").

Pure function: takes already-extracted (M4) questions and exam evidence for
one analysis and returns a single RuleFindingResult. Never touches the
database or the filesystem, so it can be unit-tested with plain in-memory
Question/Evidence instances.

Deterministic mapping from the official KB rule row to code, in evaluation
order:
1. Not_Satisfied_Condition for required missing marks. A standalone scorable
   question without a mark is a defect. Within a scored parent/container,
   partially marked child groups are also a defect, while a child group with no
   individual child marks at all may legitimately use the parent total as a
   section-level mark.
2. Not_Applicable_Condition ("No declared total is provided") when required
   question marks are otherwise complete and no declared total can be checked.
3. Not_Satisfied_Condition for a mathematically proven parent/child mark
   inconsistency, evaluated only after the child total is complete.
4. Satisfied_Condition ("The calculated total equals the declared total").
5. Partially_Satisfied_Condition ("The difference is attributable to one
   ambiguous extracted mark requiring review") - exactly one mark source
   used in the calculation has low confidence while every other used mark is
   fully confident.
6. Not_Satisfied_Condition ("The calculated total differs from the declared
   total") - any other mismatch.

Mark policy for a hierarchical question branch:
- A standalone leaf/scorable question must carry its own mark.
- For sibling child questions under a scored parent/container, an all-unmarked
  group is accepted as section-level marking: the parent total is authoritative
  for that branch and the children are not treated as individually missing.
- If some sibling child questions have individual marks and others do not, the
  unmarked children are a mark-completeness failure and are reported by label.
- When all child marks are present, their total is checked against the parent.
- When the parent mark is absent, unresolved child marks remain a completeness
  failure and complete child marks are summed for the branch.
- Child marks are never double-counted in the overall exam-total calculation.
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
_MARK_TOLERANCE = Decimal("0.000001")


@dataclass(frozen=True)
class _MarkContribution:
    label: str
    value: Decimal
    confidence: float
    evidence_labels: tuple[str, ...]


@dataclass(frozen=True)
class _HierarchyMismatch:
    parent_label: str
    parent_value: Decimal
    child_total: Decimal
    evidence_labels: tuple[str, ...]
    is_lower_bound: bool = False



def _missing_scorable_mark_labels(questions: Sequence[Question]) -> list[str]:
    """Return only *required* missing leaf/scorable marks.

    Section-level marking is valid when a parent/container has a mark and none
    of its direct leaf children carries an individual mark. Once any sibling
    leaf has an individual mark, however, the unmarked siblings form a partial
    child-level allocation and must be reported. Standalone leaves and leaves
    under an unscored parent always require their own resolvable mark.

    The rule is structural rather than question-type-specific, so it works for
    T/F, MCQ, short-answer, or other grouped formats without hard-coded labels.
    """

    by_id = {question.id: question for question in questions}
    children_by_parent: dict[uuid.UUID, list[Question]] = defaultdict(list)
    for question in questions:
        if (
            question.parent_question_id is not None
            and question.parent_question_id in by_id
        ):
            children_by_parent[question.parent_question_id].append(question)

    leaf_ids = {
        question.id for question in questions if question.id not in children_by_parent
    }
    direct_leaf_children_by_parent: dict[uuid.UUID, list[Question]] = defaultdict(list)
    for parent_id, children in children_by_parent.items():
        direct_leaf_children_by_parent[parent_id] = [
            child for child in children if child.id in leaf_ids
        ]

    missing: list[Question] = []
    for question in questions:
        if question.id not in leaf_ids or question.marks is not None:
            continue

        parent = (
            by_id.get(question.parent_question_id)
            if question.parent_question_id is not None
            else None
        )
        if parent is None:
            missing.append(question)
            continue

        leaf_siblings = direct_leaf_children_by_parent.get(parent.id, [])
        any_sibling_has_mark = any(
            sibling.marks is not None for sibling in leaf_siblings
        )

        # A scored section may intentionally put the mark only on the parent
        # when none of its peer child questions has an individual mark.
        if parent.marks is not None and leaf_siblings and not any_sibling_has_mark:
            continue

        missing.append(question)

    missing.sort(key=lambda question: (question.sequence, question.number_label))
    return [question.number_label for question in missing]

def _hierarchical_marks_mismatches(
    questions: Sequence[Question],
) -> list[_HierarchyMismatch]:
    """Return parent/child inconsistencies after child marks are complete.

    Callers report missing scorable leaf marks before invoking this consistency
    check. The defensive unresolved-path handling remains for nested or malformed
    input, but normal confirmed-review evaluation compares only complete child
    totals with the parent/container mark.
    """

    by_id = {question.id: question for question in questions}
    children_by_parent: dict[uuid.UUID, list[Question]] = defaultdict(list)
    for question in questions:
        if (
            question.parent_question_id is not None
            and question.parent_question_id in by_id
        ):
            children_by_parent[question.parent_question_id].append(question)

    for children in children_by_parent.values():
        children.sort(key=lambda question: (question.sequence, question.number_label))

    def resolve_branch(question: Question) -> tuple[Decimal | None, tuple[str, ...]]:
        if question.marks is not None:
            return Decimal(str(question.marks)), (question.number_label,)
        children = children_by_parent.get(question.id, [])
        if not children:
            return None, ()

        total = Decimal("0")
        labels: list[str] = []
        for child in children:
            value, child_labels = resolve_branch(child)
            if value is None:
                return None, tuple(labels)
            total += value
            labels.extend(child_labels)
        return total, tuple(labels)

    mismatches: list[_HierarchyMismatch] = []
    for parent in questions:
        children = children_by_parent.get(parent.id, [])
        if parent.marks is None or not children:
            continue

        parent_value = Decimal(str(parent.marks))
        known_total = Decimal("0")
        evidence_labels: list[str] = [parent.number_label]
        unresolved = False
        for child in children:
            value, labels = resolve_branch(child)
            if value is None:
                unresolved = True
                continue
            known_total += value
            evidence_labels.extend(labels)

        if unresolved:
            if known_total > parent_value + _MARK_TOLERANCE:
                mismatches.append(
                    _HierarchyMismatch(
                        parent_label=parent.number_label,
                        parent_value=parent_value,
                        child_total=known_total,
                        evidence_labels=tuple(evidence_labels),
                        is_lower_bound=True,
                    )
                )
            continue

        if abs(known_total - parent_value) > _MARK_TOLERANCE:
            mismatches.append(
                _HierarchyMismatch(
                    parent_label=parent.number_label,
                    parent_value=parent_value,
                    child_total=known_total,
                    evidence_labels=tuple(evidence_labels),
                )
            )

    return mismatches


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

    missing_scorable = _missing_scorable_mark_labels(questions)
    if missing_scorable:
        missing_evidence_ids: list[uuid.UUID] = []
        seen_ids: set[uuid.UUID] = set()
        if declared_total_evidence is not None:
            missing_evidence_ids.append(declared_total_evidence.id)
            seen_ids.add(declared_total_evidence.id)
        for label in missing_scorable:
            text_ev = text_evidence_by_label.get(label)
            if text_ev is not None and text_ev.id not in seen_ids:
                missing_evidence_ids.append(text_ev.id)
                seen_ids.add(text_ev.id)

        return RuleFindingResult(
            status=AcademicStatus.NOT_SATISFIED,
            explanation=(
                "Individual marks are missing for scorable questions: "
                f"{', '.join(missing_scorable)}. "
                "A parent/container total may represent a section when none of "
                "its child questions has an individual mark, but partial "
                "child-level marking leaves the unmarked questions unresolved. "
                "Parent-child total consistency can be checked after the "
                "required missing marks are provided."
            ),
            confidence=min(
                (
                    text_evidence_by_label[label].confidence
                    for label in missing_scorable
                    if label in text_evidence_by_label
                ),
                default=1.0,
            ),
            evidence_ids=missing_evidence_ids,
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

    hierarchy_mismatches = _hierarchical_marks_mismatches(questions)
    if hierarchy_mismatches:
        evidence_ids: list[uuid.UUID] = [declared_total_evidence.id]
        seen_ids = {declared_total_evidence.id}
        details: list[str] = []
        for mismatch in hierarchy_mismatches:
            for label in mismatch.evidence_labels:
                for ev in (
                    text_evidence_by_label.get(label),
                    marks_evidence_by_label.get(label),
                ):
                    if ev is not None and ev.id not in seen_ids:
                        evidence_ids.append(ev.id)
                        seen_ids.add(ev.id)
            if mismatch.is_lower_bound:
                details.append(
                    f"{mismatch.parent_label} is assigned {mismatch.parent_value} marks, "
                    f"while its already-confirmed child marks total at least "
                    f"{mismatch.child_total}"
                )
            else:
                details.append(
                    f"{mismatch.parent_label} is assigned {mismatch.parent_value} marks, "
                    f"while its confirmed child marks total {mismatch.child_total}"
                )
        return RuleFindingResult(
            status=AcademicStatus.NOT_SATISFIED,
            explanation="Confirmed marks inconsistency: " + "; ".join(details) + ".",
            confidence=1.0,
            evidence_ids=evidence_ids,
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
        missing_evidence_ids = list(base_evidence_ids)
        seen_ids = set(missing_evidence_ids)
        for label in missing:
            text_ev = text_evidence_by_label.get(label)
            if text_ev is not None and text_ev.id not in seen_ids:
                missing_evidence_ids.append(text_ev.id)
                seen_ids.add(text_ev.id)

        return RuleFindingResult(
            status=AcademicStatus.NOT_SATISFIED,
            explanation=(
                "One or more required mark values are missing for: "
                f"{', '.join(missing)}."
            ),
            confidence=min(
                (
                    text_evidence_by_label[label].confidence
                    for label in missing
                    if label in text_evidence_by_label
                ),
                default=1.0,
            ),
            evidence_ids=missing_evidence_ids,
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
