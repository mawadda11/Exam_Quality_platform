"""CLO Relevance (REQ002/RULE002), CLO Coverage Distribution
(REQ006/RULE006), and Out-of-Scope Content (REQ008/RULE008).

All three official KB rules require judgment this deterministic milestone
cannot make without inventing logic:
- RULE002/RULE008 are KB-classified "Semantic Rule"s asking whether an
  existing mapping's content is genuinely *relevant*, or whether question
  content that lacks a topic citation is *actually* out of scope - citation
  presence/absence (the only deterministic signal available) answers a
  different question ("was a mapping declared") than either of these ask
  ("is the mapping/content good"). There is no non-invented deterministic
  proxy for either.
- RULE006 is a KB-classified "Descriptive Rule" whose Satisfied vs.
  Partially Satisfied split depends on the *degree* of concentration across
  CLOs ("noticeably concentrated" vs. not) - a numeric threshold the KB
  does not define.

Rather than omit these three official rules entirely, each still produces
one official Finding per analysis: Not Verified with an explanation naming
exactly what is missing (semantic evaluation, or an official threshold),
linked to the same real, already-persisted question/CLO/topic evidence the
sibling rule (REQ001/REQ005/REQ007 respectively) would use - no new
Evidence rows. RULE006's KB row is the one exception with a cleanly
checkable Not_Applicable_Condition ("Only one CLO is applicable"), honored
here since it requires no invented logic, only counting.
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
from app.services.rules.types import RuleFindingResult

_CLO_RELEVANCE_EXPLANATION = (
    "REQ002 (CLO Relevance) is a KB-classified Semantic Rule: it asks whether the "
    "expected answer clearly provides relevant evidence for its mapped CLO, which is a "
    "judgment about content quality, not citation presence. Deterministic M8 has no "
    "non-invented way to assess relevance, so only Not Verified is produced."
)
_OUT_OF_SCOPE_EXPLANATION = (
    "REQ008 (Out-of-Scope Content) is a KB-classified Semantic Rule: the absence of an "
    "explicit topic citation does not deterministically prove content falls outside "
    "documented topics. Deterministic M8 has no non-invented way to assess subject-matter "
    "scope, so only Not Verified is produced."
)
_COVERAGE_DISTRIBUTION_EXPLANATION = (
    "REQ006 (CLO Coverage Distribution) is a KB-classified Descriptive Rule requiring a "
    "judgment of how concentrated evidence is across applicable CLOs, which needs a "
    "numeric threshold the knowledge base does not define. Deterministic M8 has no "
    "non-invented threshold for this, so only Not Verified is produced."
)
_SINGLE_CLO_EXPLANATION = "Only one CLO is applicable, so coverage distribution does not apply."


def _gather_evidence_ids(
    leaves: Sequence[Question],
    evidence: Sequence[Evidence],
    codes: Sequence[str],
    code_evidence_type: str,
) -> list[uuid.UUID]:
    text_evidence_by_label = {
        e.item_reference: e for e in evidence if e.evidence_type == "question_text"
    }
    code_evidence_by_code = {
        e.item_reference: e for e in evidence if e.evidence_type == code_evidence_type
    }
    evidence_ids: list[uuid.UUID] = []
    for leaf in leaves:
        text_ev = text_evidence_by_label.get(leaf.number_label)
        if text_ev is not None:
            evidence_ids.append(text_ev.id)
    for code in codes:
        code_ev = code_evidence_by_code.get(code)
        if code_ev is not None:
            evidence_ids.append(code_ev.id)
    return evidence_ids


def evaluate_clo_relevance(
    questions: Sequence[Question], evidence: Sequence[Evidence], clos: Sequence[Clo]
) -> RuleFindingResult:
    leaves = scorable_leaves(questions)
    codes = [clo.code for clo in clos]
    return RuleFindingResult(
        status=AcademicStatus.NOT_VERIFIED,
        explanation=_CLO_RELEVANCE_EXPLANATION,
        confidence=1.0,
        evidence_ids=_gather_evidence_ids(leaves, evidence, codes, "clo"),
    )


def evaluate_out_of_scope_content(
    questions: Sequence[Question], evidence: Sequence[Evidence], topics: Sequence[Topic]
) -> RuleFindingResult:
    leaves = scorable_leaves(questions)
    codes = [topic.code for topic in topics if topic.code is not None]
    return RuleFindingResult(
        status=AcademicStatus.NOT_VERIFIED,
        explanation=_OUT_OF_SCOPE_EXPLANATION,
        confidence=1.0,
        evidence_ids=_gather_evidence_ids(leaves, evidence, codes, "topic"),
    )


def evaluate_clo_coverage_distribution(
    questions: Sequence[Question], evidence: Sequence[Evidence], clos: Sequence[Clo]
) -> RuleFindingResult:
    if len(clos) == 1:
        code_evidence = [
            e for e in evidence if e.evidence_type == "clo" and e.item_reference == clos[0].code
        ]
        return RuleFindingResult(
            status=AcademicStatus.NOT_APPLICABLE,
            explanation=_SINGLE_CLO_EXPLANATION,
            confidence=1.0,
            evidence_ids=[e.id for e in code_evidence],
        )

    leaves = scorable_leaves(questions)
    codes = [clo.code for clo in clos]
    return RuleFindingResult(
        status=AcademicStatus.NOT_VERIFIED,
        explanation=_COVERAGE_DISTRIBUTION_EXPLANATION,
        confidence=1.0,
        evidence_ids=_gather_evidence_ids(leaves, evidence, codes, "clo"),
    )
