"""Focused drift guard: confirms 11_scoring_policy.xlsx's declared policy
still matches app/services/rules/scoring.py's actual behavior. No conflict
was found between the two during M7 implementation - this guards against
either one silently drifting from the other in the future. Per the approved
M7 decisions: this test never loads the workbook during a real analysis; it
only runs here, in the test suite. calculate_overall_score itself is
untouched.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from app.core.domain import AcademicStatus
from app.services.knowledge_base.loader import load_workbook
from app.services.knowledge_base.schemas import SCORING_POLICY
from app.services.rules.scoring import calculate_overall_score

REAL_KB_SOURCE = Path(__file__).resolve().parents[2] / "knowledge_base" / "source"


def _policy_values() -> dict[str, str]:
    raw = load_workbook(REAL_KB_SOURCE, SCORING_POLICY)
    return {str(row.values["Policy_Name"]): str(row.values["Policy_Value"]) for row in raw.rows}


def test_status_weights_match_scoring_py() -> None:
    policy = _policy_values()
    assert policy["Satisfied Value"] == "1.0"
    assert policy["Partially Satisfied Value"] == "0.5"
    assert policy["Not Satisfied Value"] == "0.0"

    assert calculate_overall_score([AcademicStatus.SATISFIED]).score == Decimal("100.00")
    assert calculate_overall_score([AcademicStatus.PARTIALLY_SATISFIED]).score == Decimal("50.00")
    assert calculate_overall_score([AcademicStatus.NOT_SATISFIED]).score == Decimal("0.00")


def test_not_verified_is_excluded_from_denominator() -> None:
    policy = _policy_values()
    assert policy["Not Verified Exclusion"] == "Exclude"

    result = calculate_overall_score([AcademicStatus.SATISFIED, AcademicStatus.NOT_VERIFIED])
    assert result.denominator == 1
    assert result.score == Decimal("100.00")


def test_not_applicable_is_excluded_from_denominator() -> None:
    policy = _policy_values()
    assert policy["Not Applicable Exclusion"] == "Exclude"

    result = calculate_overall_score([AcademicStatus.SATISFIED, AcademicStatus.NOT_APPLICABLE])
    assert result.denominator == 1
    assert result.score == Decimal("100.00")


def test_no_scorable_rules_yields_insufficient_evidence_per_policy() -> None:
    policy = _policy_values()
    assert policy["No Verified Rules"] == "No score generated"

    result = calculate_overall_score([AcademicStatus.NOT_VERIFIED, AcademicStatus.NOT_APPLICABLE])
    assert result.score is None
    assert result.denominator == 0
    assert result.label == "Insufficient Evidence"


def test_formula_matches_kb_declared_formula() -> None:
    policy = _policy_values()
    assert policy["Overall Score"] == (
        "Sum of status values divided by number of verified applicable rules multiplied by 100"
    )
    # (1.0 + 0.5) / 2 * 100 = 75.00, per the formula above.
    result = calculate_overall_score([AcademicStatus.SATISFIED, AcademicStatus.PARTIALLY_SATISFIED])
    assert result.score == Decimal("75.00")
    assert result.denominator == 2


def test_equal_rule_contribution_matches_scoring_py() -> None:
    policy = _policy_values()
    assert policy["Equal Rule Contribution"] == "Equal"
    # No per-rule weighting exists in calculate_overall_score - every scored
    # status contributes the same way regardless of which rule produced it.
    mixed_order_a = calculate_overall_score(
        [AcademicStatus.SATISFIED, AcademicStatus.NOT_SATISFIED]
    )
    mixed_order_b = calculate_overall_score(
        [AcademicStatus.NOT_SATISFIED, AcademicStatus.SATISFIED]
    )
    assert mixed_order_a.score == mixed_order_b.score == Decimal("50.00")
