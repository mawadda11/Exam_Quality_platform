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
   unreadable") - a scorable leaf question has marks=None.
3. Satisfied_Condition ("The calculated total equals the declared total").
4. Partially_Satisfied_Condition ("The difference is attributable to one
   ambiguous extracted mark requiring review") - exactly one leaf's marks
   came from a low-confidence extraction (Question.confidence < 1.0, i.e.
   the text match and its position didn't agree - see
   digital_pdf_extractor.py) while every other leaf is fully confident.
5. Not_Satisfied_Condition ("The calculated total differs from the declared
   total") - any other mismatch.

Double-counting avoidance: a question counts as a scorable "leaf" only if it
has no children (a standalone top-level question, or any sub-question) - a
top-level question that has sub-questions is excluded, so its own marks
value (if any) is never added on top of its children's marks.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from decimal import Decimal

from app.core.domain import AcademicStatus
from app.models.evidence import Evidence
from app.models.question import Question
from app.services.extraction.digital_pdf_extractor import TOTAL_MARKS_PATTERN
from app.services.rules.question_hierarchy import scorable_leaves
from app.services.rules.types import RuleFindingResult

_NOT_APPLICABLE_EXPLANATION = "No declared total marks were found in the exam."


def _parse_declared_total(text: str) -> Decimal | None:
    match = TOTAL_MARKS_PATTERN.match(text.strip())
    if match is None:
        return None
    return Decimal(match.group(1))


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
        # Evidence was classified as declared_total at extraction time, so this
        # should not happen; treated the same as no declared total being usable.
        return RuleFindingResult(
            status=AcademicStatus.NOT_APPLICABLE,
            explanation=_NOT_APPLICABLE_EXPLANATION,
            confidence=declared_total_evidence.confidence,
            evidence_ids=[declared_total_evidence.id],
        )

    leaves = scorable_leaves(questions)
    base_evidence_ids: list[uuid.UUID] = [declared_total_evidence.id]
    for leaf in leaves:
        text_ev = text_evidence_by_label.get(leaf.number_label)
        if text_ev is not None:
            base_evidence_ids.append(text_ev.id)
        marks_ev = marks_evidence_by_label.get(leaf.number_label)
        if marks_ev is not None:
            base_evidence_ids.append(marks_ev.id)

    missing = [leaf for leaf in leaves if leaf.marks is None]
    if missing:
        return RuleFindingResult(
            status=AcademicStatus.NOT_VERIFIED,
            explanation=(
                "One or more required mark values could not be read for: "
                f"{', '.join(leaf.number_label for leaf in missing)}."
            ),
            confidence=min((leaf.confidence for leaf in leaves), default=0.0),
            evidence_ids=base_evidence_ids,
        )

    calculated_total = sum((Decimal(str(leaf.marks)) for leaf in leaves), start=Decimal("0"))
    confidence = min((leaf.confidence for leaf in leaves), default=1.0)

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

    ambiguous = [leaf for leaf in leaves if leaf.confidence < 1.0]
    if len(ambiguous) == 1:
        return RuleFindingResult(
            status=AcademicStatus.PARTIALLY_SATISFIED,
            explanation=(
                f"Calculated total marks ({calculated_total}) differ from the declared "
                f"total marks ({declared_total}); the difference is attributable to one "
                f"ambiguous extracted mark ({ambiguous[0].number_label}) requiring review."
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
