"""Applicable CLO Coverage (REQ005/RULE005), Applicable Topic Coverage
(REQ009/RULE009), and CLO Coverage Distribution (REQ006/RULE006). Pure
functions - same shape as clo_topic_alignment.py.

REQ005/REQ009 ask "does at least one scorable question explicitly cite this
code" (app.services.rules.references) per target CLO/topic, aggregated
using a deterministic all/some/none split:
- Satisfied_Condition - every applicable CLO/topic has at least one citing
  question.
- Partially_Satisfied_Condition - at least one, but not every, applicable
  CLO/topic has a citing question.
- Not_Verified_Condition - zero scorable questions; zero CLOs/topics
  extracted; (topics only) a topic exists with no identifiable code, so the
  full intended topic set can't be reliably determined; OR zero applicable
  CLOs/topics have any citing question at all. An absence of citations is
  evidence we *lack*, not evidence *of* non-coverage - it must never be
  reported as Not Satisfied (a real, disprovable claim this deterministic
  approach cannot actually make).
- Not_Applicable_Condition - REQ009 only ("No topic set is designated for
  the uploaded exam"); REQ005 declares "None" and so never returns this.
- Not_Satisfied_Condition - never reachable by this heuristic; see above.

REQ006 (CLO Coverage Distribution) is only genuinely deterministic for two
of its five KB-declared statuses:
- 0 applicable CLOs -> Not Verified (required source data unavailable).
- exactly 1 applicable CLO -> Not Applicable (the KB's own literal
  condition: "Only one CLO is applicable.").
- 2+ applicable CLOs -> evaluate_clo_coverage_distribution returns None and
  the caller must not persist a Finding. Distinguishing Satisfied from
  Partially Satisfied here requires judging the *degree* of evidence
  concentration, and the KB defines no numeric threshold for that
  judgment - so, per the M8 correction, this is treated as an unsupported
  capability (see app.services.rules.capability_manifest), not an
  unconditional Not Verified Finding.
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


def _evaluate_coverage(
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

    covered: set[str] = set()
    for leaf in leaves:
        covered |= find_cited_codes(leaf.question_text, codes)
    uncovered = sorted(code for code in codes if code not in covered)

    evidence_ids: list[uuid.UUID] = []
    for leaf in leaves:
        text_ev = text_evidence_by_label.get(leaf.number_label)
        if text_ev is not None:
            evidence_ids.append(text_ev.id)
    for code in codes:
        code_ev = code_evidence_by_code.get(code)
        if code_ev is not None:
            evidence_ids.append(code_ev.id)

    confidence = min((leaf.confidence for leaf in leaves), default=1.0)

    if not uncovered:
        return RuleFindingResult(
            status=AcademicStatus.SATISFIED,
            explanation=f"Every applicable {target_noun} has at least one supporting question.",
            confidence=confidence,
            evidence_ids=evidence_ids,
        )
    if not covered:
        return RuleFindingResult(
            status=AcademicStatus.NOT_VERIFIED,
            explanation=(
                f"No applicable {target_noun} has any explicit deterministic citation, so "
                "coverage cannot be verified from available evidence - absence of citations "
                "does not prove non-coverage."
            ),
            confidence=confidence,
            evidence_ids=evidence_ids,
        )
    return RuleFindingResult(
        status=AcademicStatus.PARTIALLY_SATISFIED,
        explanation=(
            f"{len(covered)} of {len(codes)} applicable {target_noun}s have supporting "
            f"question evidence; no citation found for: {', '.join(uncovered)}."
        ),
        confidence=confidence,
        evidence_ids=evidence_ids,
    )


def evaluate_applicable_clo_coverage(
    questions: Sequence[Question], evidence: Sequence[Evidence], clos: Sequence[Clo]
) -> RuleFindingResult:
    return _evaluate_coverage(
        questions,
        evidence,
        codes=[clo.code for clo in clos],
        code_evidence_type="clo",
        target_noun="CLO",
        no_targets_explanation="No CLOs were extracted from the TP-153.",
    )


def evaluate_applicable_topic_coverage(
    questions: Sequence[Question], evidence: Sequence[Evidence], topics: Sequence[Topic]
) -> RuleFindingResult:
    if not topics:
        return RuleFindingResult(
            status=AcademicStatus.NOT_APPLICABLE,
            explanation="No topic set is designated for the uploaded exam.",
            confidence=1.0,
            evidence_ids=[],
        )
    if any(topic.code is None for topic in topics):
        return RuleFindingResult(
            status=AcademicStatus.NOT_VERIFIED,
            explanation="One or more intended topics have no identifiable code.",
            confidence=0.0,
            evidence_ids=[],
        )
    return _evaluate_coverage(
        questions,
        evidence,
        codes=[topic.code for topic in topics if topic.code is not None],
        code_evidence_type="topic",
        target_noun="topic",
        no_targets_explanation="No topics were extracted from the TP-153.",
    )


def evaluate_clo_coverage_distribution(
    evidence: Sequence[Evidence], clos: Sequence[Clo]
) -> RuleFindingResult | None:
    """Returns None (never Not Verified) when 2+ CLOs are applicable - the
    caller must skip persist_finding in that case rather than record an
    unconditional Finding for a judgment this engine cannot make."""
    if not clos:
        return RuleFindingResult(
            status=AcademicStatus.NOT_VERIFIED,
            explanation=(
                "No CLOs were extracted from the TP-153, so coverage distribution cannot be "
                "assessed."
            ),
            confidence=0.0,
            evidence_ids=[],
        )
    if len(clos) == 1:
        clo_evidence_ids = [
            e.id for e in evidence if e.evidence_type == "clo" and e.item_reference == clos[0].code
        ]
        return RuleFindingResult(
            status=AcademicStatus.NOT_APPLICABLE,
            explanation="Only one CLO is applicable, so coverage distribution does not apply.",
            confidence=1.0,
            evidence_ids=clo_evidence_ids,
        )
    return None
