"""Numbering and duplicate-numbering rule (REQ019 / RULE019 - "Consistent
Numbering").

Pure function: same shape and testing approach as marks_total.py.

Deterministic mapping from the official KB rule row to code:
- Not_Verified_Condition ("OCR reading order is unreliable") - this
  extractor never performs OCR (digital text layer only, see
  digital_pdf_extractor.py's module docstring), so the literal OCR condition
  can never fire from it. The closest faithful, non-invented proxy available
  from a digital-only extractor is "zero questions were extracted at all",
  i.e. there is no numbering evidence whatsoever to check - treated as Not
  Verified rather than a false Satisfied. See the M6 implementation report
  for this explicit scope decision.
- Not_Satisfied_Condition ("Duplicate ... numbering affects item
  identification") - a duplicate top-level number_label, or a duplicate
  child number_label under the same parent.
- Satisfied_Condition ("numbering is ... unique and consistent") - no
  duplicates found. Scope note: this rule checks uniqueness/duplication,
  the only numbering defect the M6 spec explicitly names; it does not check
  sequence completeness (gaps), which is a separate, unstated interpretation
  this milestone does not invent.
- Partially_Satisfied_Condition ("Minor numbering inconsistency ... without
  affecting item identification") has no available structural signal to
  detect deterministically beyond duplicate-detection (which is already the
  Not_Satisfied path) - not reachable by this heuristic; documented as a
  known limitation rather than approximated with an invented threshold.

Child-numbering handling: number_label for a sub-question is always
parent-prefixed by the extractor (e.g. "Q2(a)"), so "Q2(a)" and "Q3(a)"
never collide as plain strings. Duplicates are still checked separately,
grouped by parent_question_id, exactly as the spec requires, rather than
relying solely on that string-prefixing accident.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from uuid import UUID

from app.core.domain import AcademicStatus
from app.models.evidence import Evidence
from app.models.question import Question
from app.services.rules.types import RuleFindingResult

_NOT_VERIFIED_EXPLANATION = "No question numbering evidence was extracted from the exam."
_SATISFIED_EXPLANATION = (
    "Question numbering is unique and consistent across all top-level questions and sub-questions."
)


def _duplicate_labels(labels: Sequence[str]) -> list[str]:
    return sorted({label for label in labels if labels.count(label) > 1})


def evaluate_numbering(
    questions: Sequence[Question], evidence: Sequence[Evidence]
) -> RuleFindingResult:
    if not questions:
        return RuleFindingResult(
            status=AcademicStatus.NOT_VERIFIED,
            explanation=_NOT_VERIFIED_EXPLANATION,
            confidence=0.0,
            evidence_ids=[],
        )

    text_evidence_by_label = {
        e.item_reference: e for e in evidence if e.evidence_type == "question_text"
    }
    evidence_ids = [
        text_evidence_by_label[q.number_label].id
        for q in questions
        if q.number_label in text_evidence_by_label
    ]

    top_level_labels = [q.number_label for q in questions if q.parent_question_id is None]
    duplicates = _duplicate_labels(top_level_labels)

    children_by_parent: dict[UUID, list[Question]] = defaultdict(list)
    for q in questions:
        if q.parent_question_id is not None:
            children_by_parent[q.parent_question_id].append(q)
    for children in children_by_parent.values():
        duplicates.extend(_duplicate_labels([c.number_label for c in children]))

    confidence = min((q.confidence for q in questions), default=0.0)

    if duplicates:
        duplicate_list = ", ".join(sorted(set(duplicates)))
        return RuleFindingResult(
            status=AcademicStatus.NOT_SATISFIED,
            explanation=f"Duplicate question numbering detected: {duplicate_list}.",
            confidence=confidence,
            evidence_ids=evidence_ids,
        )

    return RuleFindingResult(
        status=AcademicStatus.SATISFIED,
        explanation=_SATISFIED_EXPLANATION,
        confidence=confidence,
        evidence_ids=evidence_ids,
    )
