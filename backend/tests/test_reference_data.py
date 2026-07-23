"""Validates app.services.knowledge_base.reference_data against the real,
approved KB workbooks - same approach as test_capability_manifest.py and
test_scoring_policy_drift.py: read the actual knowledge_base/source files
rather than a fixture copy, so a real KB edit that breaks this module's
assumptions fails a test instead of silently drifting.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.domain import AcademicStatus
from app.services.knowledge_base.loader import load_workbook
from app.services.knowledge_base.reference_data import (
    _TRIGGER_STATUS_MATCHES,
    UnknownRequirementError,
    _trigger_matches,
    get_recommendations_for,
    get_requirement_display,
)
from app.services.knowledge_base.schemas import RECOMMENDATIONS

REPO_ROOT = Path(__file__).resolve().parents[2]
KB_SOURCE = REPO_ROOT / "knowledge_base" / "source"


# --- get_requirement_display --------------------------------------------


def test_get_requirement_display_for_a_derived_exam_requirement() -> None:
    display = get_requirement_display(KB_SOURCE, "REQ001")
    assert display.requirement_id == "REQ001"
    assert display.requirement_name == "Question-to-CLO Mapping"
    assert display.dimension == "CLO Alignment"
    assert display.source_type == "Derived Exam Requirement"
    assert display.officiality == "Derived"


def test_get_requirement_display_for_a_system_requirement() -> None:
    # REQ010 (Finding Traceability) is System Defined, not a Derived Exam
    # Requirement - the UI must be able to tell these apart (CLAUDE.md: never
    # present a derived project rule as an official quotation).
    display = get_requirement_display(KB_SOURCE, "REQ010")
    assert display.requirement_name == "Finding Traceability"
    assert display.dimension == "Traceability"
    assert display.source_type == "System Requirement"
    assert display.officiality == "System Defined"


def test_get_requirement_display_matches_runtime_rule_requirements() -> None:
    # Every requirement_id the runtime pipeline can actually attach to a
    # Finding (per capability_manifest's production entries) must resolve.
    for requirement_id, expected_name in (
        ("REQ001", "Question-to-CLO Mapping"),
        ("REQ005", "Applicable CLO Coverage"),
        ("REQ006", "CLO Coverage Distribution"),
        ("REQ007", "Question-to-Topic Alignment"),
        ("REQ009", "Applicable Topic Coverage"),
        ("REQ018", "Correct Total Marks"),
        ("REQ019", "Consistent Numbering"),
    ):
        assert get_requirement_display(KB_SOURCE, requirement_id).requirement_name == expected_name


def test_get_requirement_display_raises_for_unknown_requirement_id() -> None:
    with pytest.raises(UnknownRequirementError):
        get_requirement_display(KB_SOURCE, "REQ999")


# --- _trigger_matches: the explicit, closed Trigger_Status interpretation ---
# Direct proof of the required interpretation, independent of any KB row:
#   "Not Satisfied"                        -> matches only Not Satisfied
#   "Not Verified"                         -> matches only Not Verified
#   "Partially Satisfied or Not Satisfied"  -> matches Partially Satisfied or Not Satisfied
# No fuzzy/substring/regex matching is involved anywhere in this function -
# it is a dict lookup plus an `in` check against a frozenset of AcademicStatus
# members, both exact equality.


@pytest.mark.parametrize(
    ("trigger_status", "status", "expected"),
    [
        # "Not Satisfied" matches only Not Satisfied.
        ("Not Satisfied", AcademicStatus.NOT_SATISFIED, True),
        ("Not Satisfied", AcademicStatus.PARTIALLY_SATISFIED, False),
        ("Not Satisfied", AcademicStatus.SATISFIED, False),
        ("Not Satisfied", AcademicStatus.NOT_VERIFIED, False),
        ("Not Satisfied", AcademicStatus.NOT_APPLICABLE, False),
        # "Not Verified" matches only Not Verified.
        ("Not Verified", AcademicStatus.NOT_VERIFIED, True),
        ("Not Verified", AcademicStatus.NOT_SATISFIED, False),
        ("Not Verified", AcademicStatus.PARTIALLY_SATISFIED, False),
        ("Not Verified", AcademicStatus.SATISFIED, False),
        ("Not Verified", AcademicStatus.NOT_APPLICABLE, False),
        # "Partially Satisfied or Not Satisfied" matches either of those two,
        # and only those two.
        ("Partially Satisfied or Not Satisfied", AcademicStatus.PARTIALLY_SATISFIED, True),
        ("Partially Satisfied or Not Satisfied", AcademicStatus.NOT_SATISFIED, True),
        ("Partially Satisfied or Not Satisfied", AcademicStatus.SATISFIED, False),
        ("Partially Satisfied or Not Satisfied", AcademicStatus.NOT_VERIFIED, False),
        ("Partially Satisfied or Not Satisfied", AcademicStatus.NOT_APPLICABLE, False),
        # An unrecognized literal is ignored safely - it matches nothing,
        # for every status, rather than being guessed at.
        ("Some Unrecognized Future Value", AcademicStatus.SATISFIED, False),
        ("Some Unrecognized Future Value", AcademicStatus.PARTIALLY_SATISFIED, False),
        ("Some Unrecognized Future Value", AcademicStatus.NOT_SATISFIED, False),
        ("Some Unrecognized Future Value", AcademicStatus.NOT_VERIFIED, False),
        ("Some Unrecognized Future Value", AcademicStatus.NOT_APPLICABLE, False),
    ],
)
def test_trigger_matches_explicit_interpretation(
    trigger_status: str, status: AcademicStatus, expected: bool
) -> None:
    assert _trigger_matches(trigger_status, status) is expected


def test_trigger_status_matches_table_has_exactly_the_three_kb_literals() -> None:
    assert set(_TRIGGER_STATUS_MATCHES) == {
        "Not Satisfied",
        "Not Verified",
        "Partially Satisfied or Not Satisfied",
    }


def test_every_trigger_status_in_the_kb_is_recognized() -> None:
    # Drift guard (same pattern as test_scoring_policy_drift.py): if
    # 08_recommendations.xlsx is ever revised to use a Trigger_Status
    # literal not already in _TRIGGER_STATUS_MATCHES, this fails loudly
    # instead of that new literal being silently ignored in production.
    workbook = load_workbook(KB_SOURCE, RECOMMENDATIONS)
    kb_values = {str(row.values["Trigger_Status"]) for row in workbook.rows}
    assert kb_values <= set(_TRIGGER_STATUS_MATCHES)


# --- get_recommendations_for: the same interpretation via the real KB ----


def test_combined_trigger_matches_partially_satisfied() -> None:
    results = get_recommendations_for(KB_SOURCE, "RULE001", AcademicStatus.PARTIALLY_SATISFIED)
    assert [r.recommendation_id for r in results] == ["REC001"]
    assert results[0].title == "Map the Question to a CLO"


def test_combined_trigger_matches_not_satisfied() -> None:
    results = get_recommendations_for(KB_SOURCE, "RULE001", AcademicStatus.NOT_SATISFIED)
    assert [r.recommendation_id for r in results] == ["REC001"]


def test_combined_trigger_does_not_match_satisfied() -> None:
    assert get_recommendations_for(KB_SOURCE, "RULE001", AcademicStatus.SATISFIED) == ()


def test_combined_trigger_does_not_match_not_verified() -> None:
    # RULE001 has a *separate* Not Verified recommendation (REC031, tested
    # below) - this proves the combined-trigger row (REC001) is specifically
    # excluded for Not Verified, not that RULE001 has no results at all.
    results = get_recommendations_for(KB_SOURCE, "RULE001", AcademicStatus.NOT_VERIFIED)
    assert "REC001" not in [r.recommendation_id for r in results]


def test_combined_trigger_does_not_match_not_applicable() -> None:
    # SCORE021 (docs/SCORING_POLICY.md): Satisfied and Not Applicable never
    # trigger a corrective recommendation - falls out of the KB data itself
    # (neither is a recognized Trigger_Status key), not a special case here.
    assert get_recommendations_for(KB_SOURCE, "RULE001", AcademicStatus.NOT_APPLICABLE) == ()


def test_single_status_trigger_not_verified_still_matches_correctly() -> None:
    results = get_recommendations_for(KB_SOURCE, "RULE001", AcademicStatus.NOT_VERIFIED)
    assert [r.recommendation_id for r in results] == ["REC031"]


def test_single_status_trigger_not_satisfied_still_matches_correctly() -> None:
    # RULE029's only recommendation (REC029) declares a bare "Not Satisfied"
    # trigger, with no combined "or" phrase.
    results = get_recommendations_for(KB_SOURCE, "RULE029", AcademicStatus.NOT_SATISFIED)
    assert [r.recommendation_id for r in results] == ["REC029"]
    assert get_recommendations_for(KB_SOURCE, "RULE029", AcademicStatus.PARTIALLY_SATISFIED) == ()


def test_unknown_rule_id_returns_no_recommendations_rather_than_raising() -> None:
    # Unlike an unknown requirement_id (always a drift bug for a real
    # Finding), a rule genuinely having no KB recommendation row is a valid
    # state - must not raise.
    assert get_recommendations_for(KB_SOURCE, "RULE999", AcademicStatus.NOT_SATISFIED) == ()


# --- No duplicate recommendations ----------------------------------------


def test_no_duplicate_recommendations_for_a_combined_trigger_rule() -> None:
    for status in AcademicStatus:
        results = get_recommendations_for(KB_SOURCE, "RULE001", status)
        ids = [r.recommendation_id for r in results]
        assert len(ids) == len(set(ids))


def test_no_duplicate_recommendations_across_every_rule_and_status_in_the_kb() -> None:
    # Broad sweep over the real, approved KB: for every Rule_ID it declares
    # and every possible AcademicStatus, the returned recommendation_ids are
    # never repeated within a single call.
    workbook = load_workbook(KB_SOURCE, RECOMMENDATIONS)
    rule_ids = {str(row.values["Rule_ID"]) for row in workbook.rows}
    for rule_id in rule_ids:
        for status in AcademicStatus:
            results = get_recommendations_for(KB_SOURCE, rule_id, status)
            ids = [r.recommendation_id for r in results]
            assert len(ids) == len(set(ids)), (rule_id, status, ids)
