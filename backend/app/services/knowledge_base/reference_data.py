"""Read-only, exact-ID KB reference lookups for M9 Results UI display.

This is deliberately NOT "KB retrieval" in the RAG_AND_AI_DESIGN.md sense -
app.services.processing.stages.run_retrieving_knowledge remains an
intentional no-op placeholder for that (similarity/embedding-based
retrieval feeding semantic evaluators, still a later milestone). This
module does something narrower and fully deterministic: given a
requirement_id or rule_id a Finding already carries, look up that exact
row's official display text (04_requirements.xlsx) or matching
recommendation row (08_recommendations.xlsx). No ranking, no embeddings,
no invented thresholds - an exact-match join only, cached in-process since
the KB source files are read-only-mounted (docs/ARCHITECTURE.md) and change
only with a new reviewed KB version.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.core.domain import AcademicStatus
from app.services.knowledge_base.loader import load_workbook
from app.services.knowledge_base.schemas import RECOMMENDATIONS, REQUIREMENTS


@dataclass(frozen=True)
class RequirementDisplay:
    """Official display metadata for one Requirement_ID, verbatim from
    04_requirements.xlsx. source_type/officiality exist so the UI can
    honor CLAUDE.md's "do not present derived project rules as official
    quotations" - every KB requirement is either "Derived Exam Requirement"
    or "System Requirement" (Source_Type), never itself an official
    standard quotation."""

    requirement_id: str
    requirement_name: str
    dimension: str
    source_type: str
    officiality: str


@dataclass(frozen=True)
class RecommendationDisplay:
    recommendation_id: str
    rule_id: str
    title: str
    text: str
    target_user: str
    recommendation_type: str


@dataclass(frozen=True)
class _RecommendationRow:
    # The raw Trigger_Status cell, verbatim - never split/normalized here,
    # so the stored value always matches the workbook exactly (requirement:
    # "preserve the official KB workbook values exactly as they are").
    trigger_status: str
    display: RecommendationDisplay


# Explicit, closed interpretation of every literal Trigger_Status value the
# approved 08_recommendations.xlsx actually contains (all three are checked
# against the real workbook by
# test_reference_data.py::test_every_trigger_status_in_the_kb_is_recognized).
# Deliberately NOT a generic parser (e.g. "split on the word 'or'") - a
# Trigger_Status string that is not one of these exact three literals
# matches nothing, rather than being guessed at from its shape. Extending
# this to a fourth KB-approved combination requires a reviewed code change
# here, not automatic inference.
_TRIGGER_STATUS_MATCHES: dict[str, frozenset[AcademicStatus]] = {
    "Not Satisfied": frozenset({AcademicStatus.NOT_SATISFIED}),
    "Not Verified": frozenset({AcademicStatus.NOT_VERIFIED}),
    "Partially Satisfied or Not Satisfied": frozenset(
        {AcademicStatus.PARTIALLY_SATISFIED, AcademicStatus.NOT_SATISFIED}
    ),
}


def _trigger_matches(trigger_status: str, status: AcademicStatus) -> bool:
    """True only if `status` is one of the exact statuses the (verbatim,
    unmodified) `trigger_status` literal is defined to mean above. An
    unrecognized `trigger_status` maps to the empty frozenset via .get's
    default, so it safely matches nothing - never a guess, never an error."""
    return status in _TRIGGER_STATUS_MATCHES.get(trigger_status, frozenset())


class UnknownRequirementError(KeyError):
    """Raised when a Finding's requirement_id has no matching KB row. This
    should never happen for a real Finding - every requirement_id a Finding
    can carry originates from app.services.rules.identifiers, which
    tests/test_rule_identifiers_kb_alignment.py already checks against this
    same workbook. Raising (rather than returning a placeholder string)
    keeps a genuine KB/identifier drift bug visible instead of silently
    displaying invented text."""


@lru_cache
def _requirement_index(source_dir: Path) -> dict[str, RequirementDisplay]:
    workbook = load_workbook(source_dir, REQUIREMENTS)
    return {
        str(row.values["Requirement_ID"]): RequirementDisplay(
            requirement_id=str(row.values["Requirement_ID"]),
            requirement_name=str(row.values["Requirement_Name"]),
            dimension=str(row.values["Dimension"]),
            source_type=str(row.values["Source_Type"]),
            officiality=str(row.values["Officiality"]),
        )
        for row in workbook.rows
    }


@lru_cache
def _recommendation_index(source_dir: Path) -> dict[str, tuple[_RecommendationRow, ...]]:
    workbook = load_workbook(source_dir, RECOMMENDATIONS)
    by_rule: dict[str, list[_RecommendationRow]] = {}
    for row in workbook.rows:
        rule_id = str(row.values["Rule_ID"])
        display = RecommendationDisplay(
            recommendation_id=str(row.values["Recommendation_ID"]),
            rule_id=rule_id,
            title=str(row.values["Recommendation_Title"]),
            text=str(row.values["Recommendation_Text"]),
            target_user=str(row.values["Target_User"]),
            recommendation_type=str(row.values["Recommendation_Type"]),
        )
        trigger_status = str(row.values["Trigger_Status"])
        by_rule.setdefault(rule_id, []).append(_RecommendationRow(trigger_status, display))
    return {rule_id: tuple(rows) for rule_id, rows in by_rule.items()}


def get_requirement_display(source_dir: Path, requirement_id: str) -> RequirementDisplay:
    index = _requirement_index(source_dir)
    try:
        return index[requirement_id]
    except KeyError as exc:
        raise UnknownRequirementError(
            f"{requirement_id} has no matching row in {REQUIREMENTS.filename}. Every "
            "Finding.requirement_id must originate from app.services.rules.identifiers, "
            "which is tested against this exact workbook - this indicates a KB/identifier "
            "drift bug, not missing display data."
        ) from exc


def get_recommendations_for(
    source_dir: Path, rule_id: str, status: AcademicStatus
) -> tuple[RecommendationDisplay, ...]:
    """The KB recommendation(s) whose Trigger_Status matches `status`, per
    the explicit, closed interpretation in _TRIGGER_STATUS_MATCHES. Also
    matches SCORE021/SCORE022 (docs/SCORING_POLICY.md, sourced from
    11_scoring_policy.xlsx): Satisfied and Not Applicable findings never
    trigger a recommendation. That exclusion needs no special-casing here -
    neither is a key in _TRIGGER_STATUS_MATCHES, so the lookup simply
    returns empty. Each KB row contributes at most one entry to the result
    (one row -> one boolean match check -> at most one RecommendationDisplay),
    so no single row can produce a duplicate."""
    rows = _recommendation_index(source_dir).get(rule_id, ())
    return tuple(row.display for row in rows if _trigger_matches(row.trigger_status, status))
