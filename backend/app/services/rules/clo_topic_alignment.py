"""Question-to-CLO mapping (REQ001/RULE001) and question-to-topic alignment
(REQ007/RULE007). Pure functions - same shape and testing approach as
marks_total.py/numbering.py.

Both rules ask, per scorable question, "does this question explicitly cite
one of the target codes" (app.services.rules.references - never keyword
overlap or similarity). Aggregated across all scorable questions:
- Not_Verified_Condition - zero scorable questions, zero usable (coded)
  CLOs/topics extracted, OR zero scorable questions have any explicit
  citation. An absence of citations is evidence we *lack*, not evidence
  *of* non-alignment - it must never be reported as Not Satisfied (a real,
  disprovable claim this deterministic approach cannot actually make).
- Satisfied_Condition - every scorable question cites at least one target.
- Partially_Satisfied_Condition - some but not all do (a clean
  all/none/some three-way split - no invented threshold).
- Not_Applicable_Condition - never; both REQ001 and REQ007 declare "None".
- Not_Satisfied_Condition - never reachable by this heuristic; see above.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from app.core.domain import AcademicStatus
from app.models.clo import Clo
from app.models.evidence import Evidence
from app.models.question import Question
from app.models.topic import Topic
from app.services.rules.question_hierarchy import scorable_leaves
from app.services.rules.references import find_cited_codes
from app.services.rules.types import RuleFindingResult

_NO_QUESTIONS_EXPLANATION = "No scorable questions were extracted from the exam."


def _evaluate_alignment(
    questions: Sequence[Question],
    evidence: Sequence[Evidence],
    codes: Sequence[str],
    code_evidence_type: str,
    *,
    target_noun: str,
    no_targets_explanation: str,
) -> RuleFindingResult:
    leaves = scorable_leaves(questions)
    if not leaves:
        return RuleFindingResult(
            status=AcademicStatus.NOT_VERIFIED,
            explanation=_NO_QUESTIONS_EXPLANATION,
            confidence=0.0,
            evidence_ids=[],
        )
    if not codes:
        return RuleFindingResult(
            status=AcademicStatus.NOT_VERIFIED,
            explanation=no_targets_explanation,
            confidence=0.0,
            evidence_ids=[],
        )

    text_evidence_by_label = {
        e.item_reference: e for e in evidence if e.evidence_type == "question_text"
    }
    code_evidence_by_code = {
        e.item_reference: e for e in evidence if e.evidence_type == code_evidence_type
    }

    matches: dict[str, set[str]] = {
        leaf.number_label: find_cited_codes(leaf.question_text, codes) for leaf in leaves
    }
    matched_labels = sorted(label for label, cited in matches.items() if cited)
    unmatched_labels = sorted(label for label, cited in matches.items() if not cited)
    all_cited_codes = {code for cited in matches.values() for code in cited}

    evidence_ids: list[uuid.UUID] = []
    for leaf in leaves:
        text_ev = text_evidence_by_label.get(leaf.number_label)
        if text_ev is not None:
            evidence_ids.append(text_ev.id)
    for code in all_cited_codes:
        code_ev = code_evidence_by_code.get(code)
        if code_ev is not None:
            evidence_ids.append(code_ev.id)

    confidence = min((leaf.confidence for leaf in leaves), default=1.0)

    if not matched_labels:
        return RuleFindingResult(
            status=AcademicStatus.NOT_VERIFIED,
            explanation=(
                f"No scorable question contains an explicit deterministic {target_noun} "
                "citation, so alignment cannot be verified from available evidence - "
                "absence of a citation does not prove non-alignment."
            ),
            confidence=confidence,
            evidence_ids=evidence_ids,
        )
    if not unmatched_labels:
        return RuleFindingResult(
            status=AcademicStatus.SATISFIED,
            explanation=f"Every scorable question cites an explicit {target_noun} reference.",
            confidence=confidence,
            evidence_ids=evidence_ids,
        )
    return RuleFindingResult(
        status=AcademicStatus.PARTIALLY_SATISFIED,
        explanation=(
            f"{len(matched_labels)} of {len(leaves)} scorable questions cite an explicit "
            f"{target_noun} reference; no citation found for: {', '.join(unmatched_labels)}."
        ),
        confidence=confidence,
        evidence_ids=evidence_ids,
    )


def evaluate_question_to_clo_mapping(
    questions: Sequence[Question], evidence: Sequence[Evidence], clos: Sequence[Clo]
) -> RuleFindingResult:
    return _evaluate_alignment(
        questions,
        evidence,
        codes=[clo.code for clo in clos],
        code_evidence_type="clo",
        target_noun="CLO",
        no_targets_explanation="No CLOs were extracted from the TP-153.",
    )


def evaluate_question_to_topic_alignment(
    questions: Sequence[Question], evidence: Sequence[Evidence], topics: Sequence[Topic]
) -> RuleFindingResult:
    return _evaluate_alignment(
        questions,
        evidence,
        codes=[topic.code for topic in topics if topic.code is not None],
        code_evidence_type="topic",
        target_noun="topic",
        no_targets_explanation="No topics were extracted from the TP-153.",
    )
